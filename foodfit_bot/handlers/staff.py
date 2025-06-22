from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging
from typing import Optional

from foodfit_bot.config.database import cursor, conn
from foodfit_bot.keyboards.reply import staff_kb, cancel_kb
from foodfit_bot.keyboards.inline import build_order_control_kb
from foodfit_bot.models.states import Form
from foodfit_bot.services.database_service import (
    get_order_details,
    update_order_status,
    search_dishes,
    get_active_orders
)
from foodfit_bot.utils.helpers import format_order_date, clean_text

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "👥 Режим официанта")
@router.message(Command("staff"))
async def staff_mode(message: Message):
    """Активирует режим официанта"""
    await message.answer(
        "👨‍🍳 Режим официанта активирован",
        reply_markup=staff_kb()
    )


@router.message(F.text == "🔍 Поиск блюда")
async def search_dish_start(message: Message, state: FSMContext):
    """Начинает процесс поиска блюда"""
    await message.answer(
        "Введите название блюда или ингредиент:",
        reply_markup=cancel_kb()
    )
    await state.set_state(Form.staff_search)


@router.message(Form.staff_search)
async def process_search(message: Message, state: FSMContext):
    """Обрабатывает поисковый запрос"""
    try:
        query = clean_text(message.text)
        if not query:
            await message.answer("Пожалуйста, введите корректный запрос")
            return

        dishes = search_dishes(query)

        if not dishes:
            await message.answer("🍽 Блюд по вашему запросу не найдено")
            await state.clear()
            return

        # Показываем первые 5 результатов
        for dish in dishes[:5]:
            text = (
                f"🍽 <b>{dish['name']}</b>\n"
                f"💵 {dish['price']}₽ | 🔥 {dish['calories']} ккал\n"
                f"🏷 Теги: {dish.get('tags', 'нет')}"
            )

            await message.answer(text)

        await message.answer(
            "Поиск завершен",
            reply_markup=staff_kb()
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка поиска блюд: {e}")
        await message.answer(
            "⚠ Произошла ошибка при поиске",
            reply_markup=staff_kb()
        )
        await state.clear()


@router.message(F.text == "📊 Открытые заказы")
async def show_active_orders(message: Message):
    """Показывает активные заказы"""
    try:
        orders = get_active_orders()

        if not orders:
            await message.answer("📭 Нет активных заказов")
            return

        for order in orders:
            order_info = (
                f"🆔 <b>Заказ #{order['order_id']}</b>\n"
                f"👤 Клиент: {order['customer_name']}\n"
                f"📅 {format_order_date(order['order_date'])}\n"
                f"💵 Сумма: {order['total_amount']}₽\n"
                f"📊 Статус: {order['status']}"
            )

            await message.answer(
                order_info,
                reply_markup=build_order_control_kb(order['order_id'])
            )

    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer("⚠ Произошла ошибка при загрузке заказов")


@router.callback_query(F.data.startswith("complete_order_"))
async def complete_order(callback: CallbackQuery):
    """Отмечает заказ как выполненный"""
    try:
        order_id = int(callback.data.split("_")[2])
        if update_order_status(order_id, "завершен"):
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} отмечен как завершенный"
            )
            await callback.answer()
        else:
            await callback.answer("⚠ Не удалось обновить статус", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка завершения заказа: {e}")
        await callback.answer("⚠ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("order_details_"))
async def show_order_details(callback: CallbackQuery):
    """Показывает детали заказа"""
    try:
        order_id = int(callback.data.split("_")[2])
        order = get_order_details(order_id)

        if not order:
            await callback.answer("Заказ не найден")
            return

        items_text = "\n".join(
            f"• {item['name']} × {item['quantity']} — {item['price'] * item['quantity']}₽"
            for item in order['items']
        )

        response = (
            f"📋 <b>Заказ #{order['order_id']}</b>\n"
            f"👤 Клиент: {order['customer_name']}\n"
            f"📅 {format_order_date(order['order_date'])}\n"
            f"💵 Сумма: {order['total_amount']}₽\n"
            f"📊 Статус: {order['status']}\n\n"
            f"<b>Состав:</b>\n{items_text}"
        )

        await callback.message.answer(response)
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка загрузки деталей заказа: {e}")
        await callback.answer("⚠ Ошибка при загрузке информации", show_alert=True)


@router.message(F.text == "✅ Завершить заказ")
async def ask_order_number(message: Message, state: FSMContext):
    """Запрашивает номер заказа для завершения"""
    await message.answer(
        "Введите номер заказа для завершения:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Form.waiting_for_order_id)


@router.message(Form.waiting_for_order_id)
async def process_order_completion(message: Message, state: FSMContext):
    """Обрабатывает завершение заказа по номеру"""
    try:
        order_id = int(message.text)
        if update_order_status(order_id, "завершен"):
            await message.answer(
                f"✅ Заказ #{order_id} отмечен как завершенный",
                reply_markup=staff_kb()
            )
        else:
            await message.answer(
                "❌ Не удалось найти или обновить заказ",
                reply_markup=staff_kb()
            )
    except ValueError:
        await message.answer(
            "❌ Введите корректный номер заказа",
            reply_markup=staff_kb()
        )
    except Exception as e:
        logger.error(f"Ошибка завершения заказа: {e}")
        await message.answer(
            "⚠ Произошла ошибка",
            reply_markup=staff_kb()
        )
    finally:
        await state.clear()


@router.message(F.text == "🔄 Обновить список")
async def refresh_orders(message: Message):
    """Обновляет список заказов"""
    await show_active_orders(message)


@router.message(F.text == "🔙 Главное меню")
async def exit_staff_mode(message: Message):
    """Выход из режима официанта"""
    await message.answer(
        "Вы вышли из режима официанта",
        reply_markup=ReplyKeyboardRemove()
    )
    from foodfit_bot.keyboards.reply import main_menu_kb
    await message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb()
    )
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging
from typing import List, Optional

from foodfit_bot.config.database import cursor, conn
from foodfit_bot.keyboards.inline import build_order_control_kb
from foodfit_bot.keyboards.reply import main_menu_kb, staff_kb
from foodfit_bot.models.states import Form, DeliveryStates
from foodfit_bot.services.database_service import (
    get_order_details,
    get_user_orders,
    update_order_status
)
from foodfit_bot.utils.helpers import format_order_date

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "📦 Мои заказы")
@router.message(Command("orders"))
async def show_user_orders(message: Message):
    """Показывает историю заказов пользователя"""
    try:
        orders = get_user_orders(message.from_user.id)

        if not orders:
            await message.answer("📭 У вас пока нет заказов")
            return

        response = "📦 <b>Ваши заказы:</b>\n\n"
        for order in orders:
            response += (
                f"🆔 <b>#{order['order_id']}</b>\n"
                f"📅 {format_order_date(order['order_date'])}\n"
                f"💵 Сумма: {order['total_amount']}₽\n"
                f"📊 Статус: {order['status']}\n"
                f"————————————\n"
            )

        await message.answer(response)

    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer("⚠ Произошла ошибка при загрузке заказов")


@router.callback_query(F.data.startswith("order_details_"))
async def show_order_details_handler(callback: CallbackQuery):
    """Показывает детали конкретного заказа"""
    try:
        order_id = int(callback.data.split("_")[2])
        order = get_order_details(order_id)

        if not order:
            await callback.answer("Заказ не найден")
            return

        response = (
            f"📋 <b>Заказ #{order['order_id']}</b>\n"
            f"👤 Клиент: {order['customer_name']}\n"
            f"📅 Дата: {format_order_date(order['order_date'])}\n"
            f"💵 Сумма: {order['total_amount']}₽\n"
            f"📊 Статус: {order['status']}\n\n"
            f"<b>Состав:</b>\n"
        )

        for item in order['items']:
            response += f"• {item['name']} × {item['quantity']} — {item['price'] * item['quantity']}₽\n"

        await callback.message.answer(response)
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка загрузки деталей заказа: {e}")
        await callback.answer("⚠ Ошибка при загрузке информации", show_alert=True)


@router.message(F.text == "📊 Открытые заказы")
async def show_active_orders(message: Message):
    """Показывает активные заказы (для персонала)"""
    try:
        cursor.execute("""
            SELECT o.order_id, u.full_name, o.order_date, o.total_amount 
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.status IN ('принят', 'готовится', 'в доставке')
            ORDER BY o.order_date DESC
        """)
        orders = cursor.fetchall()

        if not orders:
            await message.answer("📭 Нет активных заказов")
            return

        response = "📊 <b>Активные заказы:</b>\n\n"
        for order in orders:
            order_id, customer, date, total = order
            response += (
                f"🆔 <b>#{order_id}</b>\n"
                f"👤 {customer}\n"
                f"📅 {format_order_date(date)}\n"
                f"💵 {total}₽\n"
                f"————————————\n"
            )

        await message.answer(
            response,
            reply_markup=staff_kb()
        )

    except Exception as e:
        logger.error(f"Ошибка загрузки активных заказов: {e}")
        await message.answer("⚠ Ошибка при загрузке заказов")


@router.callback_query(F.data.startswith("complete_order_"))
async def complete_order_handler(callback: CallbackQuery):
    """Отмечает заказ как завершенный"""
    try:
        order_id = int(callback.data.split("_")[2])
        if update_order_status(order_id, "завершен"):
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} отмечен как завершенный"
            )
        else:
            await callback.answer("⚠ Не удалось обновить статус", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка завершения заказа: {e}")
        await callback.answer("⚠ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("to_delivery_"))
async def to_delivery_handler(callback: CallbackQuery):
    """Переводит заказ в статус 'в доставке'"""
    try:
        order_id = int(callback.data.split("_")[2])
        if update_order_status(order_id, "в доставке"):
            await callback.answer("🚚 Заказ передан в доставку")
            await callback.message.edit_reply_markup(
                reply_markup=build_order_control_kb(order_id)
            )
        else:
            await callback.answer("⚠ Не удалось обновить статус", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка изменения статуса: {e}")
        await callback.answer("⚠ Произошла ошибка", show_alert=True)


@router.message(F.text == "✅ Завершить заказ")
async def ask_order_number(message: Message, state: FSMContext):
    """Запрашивает номер заказа для завершения"""
    await message.answer(
        "Введите номер заказа для завершения:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Form.waiting_for_order_id)


@router.message(Form.waiting_for_order_id)
async def complete_order_by_number(message: Message, state: FSMContext):
    """Завершает заказ по номеру"""
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


@router.message(F.text == "🚚 Оформить доставку")
async def start_delivery_process(message: Message, state: FSMContext):
    """Начинает процесс оформления доставки"""
    await message.answer(
        "Введите адрес доставки:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(DeliveryStates.waiting_address)


@router.message(DeliveryStates.waiting_address)
async def process_delivery_address(message: Message, state: FSMContext):
    """Обрабатывает адрес доставки"""
    await state.update_data(address=message.text)
    await message.answer("Введите желаемое время доставки (например, 18:00):")
    await state.set_state(DeliveryStates.waiting_time)


@router.message(DeliveryStates.waiting_time)
async def process_delivery_time(message: Message, state: FSMContext):
    """Обрабатывает время доставки"""
    await state.update_data(time=message.text)
    await message.answer("Введите номер телефона для связи:")
    await state.set_state(DeliveryStates.waiting_contact)


@router.message(DeliveryStates.waiting_contact)
async def process_delivery_contact(message: Message, state: FSMContext):
    """Завершает оформление доставки"""
    data = await state.get_data()

    # Здесь можно добавить сохранение данных доставки в БД
    await message.answer(
        f"🚚 Доставка оформлена!\n\n"
        f"Адрес: {data['address']}\n"
        f"Время: {data['time']}\n"
        f"Контакт: {message.text}",
        reply_markup=main_menu_kb()
    )
    await state.clear()
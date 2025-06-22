from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging
from typing import Optional

from foodfit_bot.config.database import cursor, conn
from foodfit_bot.keyboards.inline import (
    build_dish_keyboard,
    build_filters_keyboard,
    build_pagination_keyboard
)
from foodfit_bot.keyboards.reply import main_menu_kb
from foodfit_bot.models.states import Form
from foodfit_bot.services.database_service import get_dish_info, search_dishes

router = Router()
logger = logging.getLogger(__name__)

# Константы для пагинации
MENU_PAGE_SIZE = 5


@router.message(F.text == "🍽 Меню")
@router.message(Command("menu"))
async def show_menu(message: Message, page: int = 1):
    """
    Показывает меню с пагинацией
    """
    try:
        # Получаем общее количество блюд
        cursor.execute("SELECT COUNT(*) FROM menu")
        total_dishes = cursor.fetchone()[0]
        total_pages = (total_dishes + MENU_PAGE_SIZE - 1) // MENU_PAGE_SIZE

        # Получаем блюда для текущей страницы
        cursor.execute("""
            SELECT dish_id, name, price, calories, photo 
            FROM menu 
            ORDER BY name
            LIMIT ? OFFSET ?
        """, (MENU_PAGE_SIZE, (page - 1) * MENU_PAGE_SIZE))
        dishes = cursor.fetchall()

        if not dishes:
            await message.answer("🍽 Меню пока пусто. Зайдите позже!")
            return

        # Отправляем каждое блюдо отдельным сообщением
        for dish in dishes:
            dish_id, name, price, calories, photo = dish
            text = f"<b>{name}</b>\n\n🔥 {calories} ккал\n💵 {price}₽"

            if photo:
                await message.answer_photo(
                    photo,
                    caption=text,
                    reply_markup=build_dish_keyboard(dish_id))
            else:
                await message.answer(
                    text,
                    reply_markup=build_dish_keyboard(dish_id))

                # Добавляем пагинацию
                if total_pages > 1:
                    await message.answer(
                        f"Страница {page} из {total_pages}",
                        reply_markup=build_pagination_keyboard(
                            page=page,
                            total_pages=total_pages,
                            prefix="menu"
                        )
                    )

    except Exception as e:
        logger.error(f"Ошибка загрузки меню: {e}")
        await message.answer("⚠ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("menu_page_"))
async def menu_page_handler(callback: CallbackQuery):
    """
    Обрабатывает переключение страниц меню
    """
    page = int(callback.data.split("_")[2])
    await callback.message.delete()
    await show_menu(callback.message, page=page)


@router.callback_query(F.data.startswith("dish_detail_"))
async def show_dish_details(callback: CallbackQuery):
    """
    Показывает подробную информацию о блюде
    """
    try:
        dish_id = int(callback.data.split("_")[2])
        dish = get_dish_info(dish_id)

        if not dish:
            await callback.answer("Блюдо не найдено")
            return

        text = (
            f"🍽 <b>{dish['name']}</b>\n\n"
            f"📝 {dish['description']}\n\n"
            f"🔥 Калории: {dish['calories']} ккал\n"
            f"💵 Цена: {dish['price']}₽\n"
            f"🏷 Теги: {dish['tags'] or 'нет'}"
        )

        if dish['photo']:
            await callback.message.answer_photo(
                dish['photo'],
                caption=text,
                reply_markup=build_dish_keyboard(dish_id))
        else:
            await callback.message.answer(
                text,
                reply_markup=build_dish_keyboard(dish_id))

            await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка показа деталей блюда: {e}")
        await callback.answer("⚠ Ошибка при загрузке информации", show_alert=True)


@router.message(F.text == "⚙️ Фильтры")
@router.message(Command("filters"))
async def show_filters(message: Message):
    """
    Показывает доступные фильтры меню
    """
    await message.answer(
        "Выберите тип блюд:",
        reply_markup=build_filters_keyboard()
    )


@router.callback_query(F.data.startswith("filter_"))
async def apply_filter(callback: CallbackQuery):
    """
    Применяет выбранный фильтр к меню
    """
    filter_type = callback.data.split("_")[1]

    try:
        filters = {
            'vegan': {'vegan': True},
            'gluten_free': {'gluten_free': True},
            'spicy': {'tags': '%острое%'},
            'meat': {'tags': '%мясо%'},
            'reset': {}
        }.get(filter_type, {})

        dishes = search_dishes("", filters)

        if not dishes:
            await callback.answer("😕 По вашему запросу ничего не найдено")
            return

        # Показываем первые 5 результатов
        for dish in dishes[:5]:
            text = f"<b>{dish['name']}</b>\n\n🔥 {dish['calories']} ккал\n💵 {dish['price']}₽"
            await callback.message.answer(
                text,
                reply_markup=build_dish_keyboard(dish['dish_id']))

        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка фильтрации: {e}")
        await callback.answer("⚠ Ошибка при фильтрации", show_alert=True)


@router.message(F.text == "🔙 Назад в меню")
async def back_to_menu(message: Message):
    """
    Возвращает пользователя в главное меню
    """
    await message.answer(
        "Возвращаемся в меню:",
        reply_markup=main_menu_kb()
    )
    await show_menu(message)
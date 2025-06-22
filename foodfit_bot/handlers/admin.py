from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputFile, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from datetime import datetime
import os
import logging
from foodfit_bot.config.database import cursor, conn
from foodfit_bot.handlers.commands import admin_panel
from foodfit_bot.keyboards.reply import admin_kb, cancel_kb, main_menu_kb
from foodfit_bot.keyboards.inline import (
    build_admin_dish_edit_kb,
    build_delete_confirmation_kb
)
from foodfit_bot.models.states import Form
from foodfit_bot.services.database_service import is_admin
from foodfit_bot.services.ai_service import generate_ai_description
from foodfit_bot.utils.helpers import validate_price

router = Router()
logger = logging.getLogger(__name__)


# ---------------------- Админ-панель ----------------------
@router.message(F.text == "📝 Добавить блюдо")
async def add_dish_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return

    await state.set_state(Form.dish_name)
    await message.answer("Введите название блюда:", reply_markup=cancel_kb())


# ---------------------- Добавление блюда ----------------------
@router.message(Form.dish_name)
async def add_dish_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.dish_price)
    await message.answer("Введите цену блюда (в рублях):")


@router.message(Form.dish_price)
async def add_dish_price(message: Message, state: FSMContext):
    if not validate_price(message.text):
        await message.answer("❌ Введите корректную цену (только цифры)!")
        return

    price = int(message.text)
    await state.update_data(price=price)

    data = await state.get_data()
    dish_name = data['name']

    generating_msg = await message.answer("🧑‍🍳 Генерирую описание блюда...")
    description = await generate_ai_description(dish_name)
    await generating_msg.delete()

    await state.update_data(description=description)
    await state.set_state(Form.dish_cal)
    await message.answer(
        f"🍽 {dish_name}\n\n{description}\n\nВведите калорийность блюда:"
    )


@router.message(Form.dish_cal)
async def add_dish_calories(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число!")
        return

    calories = int(message.text)
    await state.update_data(calories=calories)
    await state.set_state(Form.dish_tags)
    await message.answer("Введите теги через запятую (веган, без глютена и т.д.):")


@router.message(Form.dish_tags)
async def add_dish_tags(message: Message, state: FSMContext):
    await state.update_data(tags=message.text)
    await state.set_state(Form.dish_photo)
    await message.answer(
        "Отправьте фото блюда или нажмите 'Пропустить':",
        reply_markup=cancel_kb()
    )


@router.message(Form.dish_photo)
async def add_dish_photo(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.text and message.text.lower() == "пропустить":
        photo_path = None
    elif message.photo:
        photo_id = message.photo[-1].file_id
        photo = await message.bot.get_file(photo_id)
        os.makedirs("photos", exist_ok=True)
        photo_path = f"photos/{photo_id}.jpg"
        await message.bot.download_file(photo.file_path, photo_path)
    else:
        await message.answer("Пожалуйста, отправьте фото или напишите 'Пропустить'")
        return

    cursor.execute(
        """INSERT INTO menu (name, description, price, calories, tags, photo) 
        VALUES (?, ?, ?, ?, ?, ?)""",
        (data['name'], data['description'], data['price'],
         data['calories'], data['tags'], photo_path)
    )
    conn.commit()

    await message.answer(
        f"✅ Блюдо успешно добавлено!\n\n"
        f"🍽 {data['name']}\n"
        f"📝 {data['description']}\n"
        f"💵 {data['price']}₽\n"
        f"🔥 {data['calories']} ккал\n"
        f"🏷 {data['tags']}",
        reply_markup=admin_kb()
    )
    await state.clear()


# ---------------------- Редактирование блюда ----------------------
@router.message(F.text == "✏️ Редактировать блюдо")
async def edit_dish_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return

    dishes = cursor.execute("SELECT dish_id, name FROM menu").fetchall()

    if not dishes:
        await message.answer("Меню пустое")
        return

    builder = types.InlineKeyboardBuilder()
    for dish_id, name in dishes:
        builder.button(text=name, callback_data=f"editdish_{dish_id}")
    builder.adjust(2)

    await message.answer(
        "Выберите блюдо для редактирования:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("editdish_"))
async def select_dish_to_edit(callback: CallbackQuery, state: FSMContext):
    dish_id = int(callback.data.split("_")[1])
    await state.update_data(dish_id=dish_id)

    await callback.message.edit_text(
        "Какое поле вы хотите изменить?",
        reply_markup=build_admin_dish_edit_kb()
    )
    await state.set_state(Form.waiting_for_edit_choice)


@router.callback_query(F.data.startswith("editfield_"), Form.waiting_for_edit_choice)
async def select_field_to_edit(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    await state.update_data(field=field)

    field_names = {
        "name": "название",
        "description": "описание",
        "price": "цену (в рублях)",
        "calories": "калорийность",
        "tags": "теги (через запятую)",
        "photo": "фото (отправьте новое изображение)"
    }

    await callback.message.edit_text(
        f"Введите новое {field_names[field]}:",
        reply_markup=cancel_kb()
    )
    await state.set_state(Form.waiting_for_edit_value)


@router.message(Form.waiting_for_edit_value)
async def save_edited_value(message: Message, state: FSMContext):
    data = await state.get_data()
    dish_id = data['dish_id']
    field = data['field']

    try:
        if field in ['price', 'calories']:
            new_value = int(message.text)
        elif field == 'photo':
            if not message.photo:
                await message.answer("Пожалуйста, отправьте фото")
                return

            # Удаляем старое фото
            old_photo = cursor.execute(
                "SELECT photo FROM menu WHERE dish_id = ?",
                (dish_id,)
            ).fetchone()[0]

            if old_photo and os.path.exists(old_photo):
                os.remove(old_photo)

            # Сохраняем новое
            photo_id = message.photo[-1].file_id
            photo = await message.bot.get_file(photo_id)
            photo_path = f"photos/{photo_id}.jpg"
            await message.bot.download_file(photo.file_path, photo_path)
            new_value = photo_path
        else:
            new_value = message.text

        cursor.execute(
            f"UPDATE menu SET {field} = ? WHERE dish_id = ?",
            (new_value, dish_id)
        )
        conn.commit()

        dish_name = cursor.execute(
            "SELECT name FROM menu WHERE dish_id = ?",
            (dish_id,)
        ).fetchone()[0]

        await message.answer(
            f"✅ Блюдо '{dish_name}' успешно обновлено!",
            reply_markup=admin_kb()
        )
    except ValueError:
        await message.answer("❌ Для этого поля нужно ввести число!")
        return
    except Exception as e:
        logger.error(f"Ошибка редактирования: {e}")
        await message.answer("⚠ Ошибка при обновлении")
    finally:
        await state.clear()


# ---------------------- Удаление блюда ----------------------
@router.message(F.text == "❌ Удалить блюдо")
async def delete_dish_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return

    dishes = cursor.execute("SELECT dish_id, name FROM menu").fetchall()

    if not dishes:
        await message.answer("Меню пустое")
        return

    builder = types.InlineKeyboardBuilder()
    for dish_id, name in dishes:
        builder.button(text=name, callback_data=f"delete_{dish_id}")
    builder.adjust(2)

    await message.answer(
        "Выберите блюдо для удаления:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("delete_"))
async def confirm_delete_dish(callback: CallbackQuery):
    dish_id = int(callback.data.split("_")[1])
    dish_name = cursor.execute(
        "SELECT name FROM menu WHERE dish_id = ?",
        (dish_id,)
    ).fetchone()[0]

    await callback.message.edit_text(
        f"Вы точно хотите удалить блюдо '{dish_name}'?",
        reply_markup=build_delete_confirmation_kb(dish_id)
    )


@router.callback_query(F.data.startswith("confirm_delete_"))
async def execute_delete_dish(callback: CallbackQuery):
    dish_id = int(callback.data.split("_")[2])
    dish_name = cursor.execute(
        "SELECT name FROM menu WHERE dish_id = ?",
        (dish_id,)
    ).fetchone()[0]

    # Удаляем фото если есть
    photo_path = cursor.execute(
        "SELECT photo FROM menu WHERE dish_id = ?",
        (dish_id,)
    ).fetchone()[0]

    if photo_path and os.path.exists(photo_path):
        os.remove(photo_path)

    cursor.execute("DELETE FROM menu WHERE dish_id = ?", (dish_id,))
    conn.commit()

    await callback.message.edit_text(
        f"✅ Блюдо '{dish_name}' успешно удалено!"
    )
    await admin_panel(callback.message)


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_dish(callback: CallbackQuery):
    await callback.message.edit_text("Удаление отменено")
    await admin_panel(callback.message)


# ---------------------- Список заказов ----------------------
@router.message(F.text == "📊 Список заказов")
async def show_orders(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Недостаточно прав")
        return

    try:
        cursor.execute("""
            SELECT o.order_id, u.full_name, o.order_date, o.total_amount 
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            ORDER BY o.order_date DESC
            LIMIT 10
        """)
        orders = cursor.fetchall()

        if not orders:
            await message.answer("📦 Нет заказов")
            return

        response = "📦 <b>Последние заказы:</b>\n\n"
        for order in orders:
            order_id, customer, date, total = order
            response += (
                f"🆔 <b>#{order_id}</b>\n"
                f"👤 {customer}\n"
                f"📅 {date}\n"
                f"💵 {total}₽\n"
                f"————————————\n"
            )

        await message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer("⚠ Ошибка при загрузке заказов")


# ---------------------- Выход из админки ----------------------
@router.message(F.text == "🔙 Выход")
async def exit_admin(message: Message):
    await message.answer(
        "Вы успешно вышли из админ-панели ✅",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb()
    )

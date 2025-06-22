from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime
import logging
from aiogram.filters import Command
from typing import Union
from foodfit_bot.config.database import cursor, conn
from foodfit_bot.keyboards.inline import build_cart_keyboard
from foodfit_bot.keyboards.reply import main_menu_kb
from foodfit_bot.services.database_service import get_dish_info

router = Router()
logger = logging.getLogger(__name__)

# ---------------------- Отображение корзины ----------------------
@router.message(F.text == "🛒 Корзина")
@router.message(Command("cart"))
async def show_cart(message: Union[Message, CallbackQuery]):
    """Показывает содержимое корзины пользователя"""
    if isinstance(message, CallbackQuery):
        user_id = message.from_user.id
        message = message.message
    else:
        user_id = message.from_user.id

    try:
        # Получаем содержимое корзины
        cursor.execute('''
            SELECT c.cart_id, c.dish_id, m.name, m.price, c.quantity, m.calories, m.photo 
            FROM cart c 
            JOIN menu m ON c.dish_id = m.dish_id 
            WHERE c.user_id = ?
        ''', (user_id,))
        items = cursor.fetchall()

        if not items:
            await message.answer("🛒 Ваша корзина пуста")
            return

        # Формируем сообщение
        total_amount = 0
        total_calories = 0
        cart_text = "🛒 <b>Ваша корзина:</b>\n\n"

        for item in items:
            _, dish_id, name, price, quantity, calories, photo = item
            item_total = price * quantity
            cart_text += f"• {name}\n   {price}₽ × {quantity} = {item_total}₽\n"
            total_amount += item_total
            total_calories += calories * quantity

        cart_text += f"\n<b>Итого:</b> {total_amount}₽\n"
        cart_text += f"<b>Калории:</b> {total_calories} ккал"

        # Отправляем сообщение с клавиатурой
        await message.answer(
            cart_text,
            reply_markup=build_cart_keyboard(items)
        )

    except Exception as e:
        logger.error(f"Ошибка отображения корзины: {e}")
        await message.answer("⚠ Произошла ошибка при загрузке корзины")

# ---------------------- Добавление в корзину ----------------------
@router.callback_query(F.data.startswith("cart_"))
async def add_to_cart(callback: CallbackQuery):
    """Добавляет блюдо в корзину"""
    try:
        user_id = callback.from_user.id
        dish_id = int(callback.data.split("_")[1])

        # Проверяем наличие блюда в корзине
        cursor.execute("""
            SELECT quantity FROM cart 
            WHERE user_id = ? AND dish_id = ?
        """, (user_id, dish_id))
        existing_item = cursor.fetchone()

        if existing_item:
            # Увеличиваем количество
            cursor.execute("""
                UPDATE cart SET quantity = quantity + 1 
                WHERE user_id = ? AND dish_id = ?
            """, (user_id, dish_id))
        else:
            # Добавляем новую запись
            cursor.execute("""
                INSERT INTO cart (user_id, dish_id, quantity)
                VALUES (?, ?, 1)
            """, (user_id, dish_id))

        conn.commit()

        # Получаем название блюда для уведомления
        dish_name = cursor.execute("""
            SELECT name FROM menu WHERE dish_id = ?
        """, (dish_id,)).fetchone()[0]

        await callback.answer(f"✅ {dish_name} добавлен(о) в корзину")

    except Exception as e:
        logger.error(f"Ошибка добавления в корзину: {e}")
        await callback.answer("⚠ Не удалось добавить в корзину", show_alert=True)

# ---------------------- Управление количеством ----------------------
@router.callback_query(F.data.startswith("increase_"))
async def increase_quantity(callback: CallbackQuery):
    """Увеличивает количество товара в корзине"""
    await _update_quantity(callback, +1)

@router.callback_query(F.data.startswith("decrease_"))
async def decrease_quantity(callback: CallbackQuery):
    """Уменьшает количество товара в корзине"""
    await _update_quantity(callback, -1)

async def _update_quantity(callback: CallbackQuery, delta: int):
    try:
        user_id = callback.from_user.id
        dish_id = int(callback.data.split("_")[1])

        # Получаем текущее количество
        cursor.execute("""
            SELECT quantity FROM cart 
            WHERE user_id = ? AND dish_id = ?
        """, (user_id, dish_id))
        current_qty = cursor.fetchone()[0]

        new_qty = current_qty + delta

        if new_qty < 1:
            await callback.answer("❌ Минимальное количество - 1")
            return

        # Обновляем количество
        cursor.execute("""
            UPDATE cart SET quantity = ? 
            WHERE user_id = ? AND dish_id = ?
        """, (new_qty, user_id, dish_id))
        conn.commit()

        await callback.answer(f"Количество изменено: {new_qty}")
        await show_cart(callback)

    except Exception as e:
        logger.error(f"Ошибка изменения количества: {e}")
        await callback.answer("⚠ Ошибка при изменении количества", show_alert=True)

# ---------------------- Удаление из корзины ----------------------
@router.callback_query(F.data.startswith("remove_"))
async def remove_item(callback: CallbackQuery):
    """Удаляет блюдо из корзины"""
    try:
        user_id = callback.from_user.id
        dish_id = int(callback.data.split("_")[1])

        cursor.execute("""
            DELETE FROM cart 
            WHERE user_id = ? AND dish_id = ?
        """, (user_id, dish_id))
        conn.commit()

        await callback.answer("🗑 Блюдо удалено из корзины")
        await show_cart(callback)

    except Exception as e:
        logger.error(f"Ошибка удаления из корзины: {e}")
        await callback.answer("⚠ Не удалось удалить блюдо", show_alert=True)

# ---------------------- Очистка корзины ----------------------
@router.callback_query(F.data == "clear_cart")
async def clear_cart_handler(callback: CallbackQuery):
    """Полностью очищает корзину пользователя"""
    try:
        user_id = callback.from_user.id

        cursor.execute("""
            DELETE FROM cart WHERE user_id = ?
        """, (user_id,))
        conn.commit()

        await callback.message.edit_text("🛒 Ваша корзина пуста")
        await callback.answer("Корзина очищена")

    except Exception as e:
        logger.error(f"Ошибка очистки корзины: {e}")
        await callback.answer("⚠ Не удалось очистить корзину", show_alert=True)

# ---------------------- Оформление заказа ----------------------
@router.callback_query(F.data == "checkout")
async def checkout_handler(callback: CallbackQuery):
    """Оформляет заказ из содержимого корзины"""
    try:
        user_id = callback.from_user.id

        # 1. Проверяем наличие товаров в корзине
        cursor.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            await callback.answer("🛒 Ваша корзина пуста!", show_alert=True)
            return

        # 2. Получаем содержимое корзины
        cursor.execute("""
            SELECT c.dish_id, m.name, m.price, c.quantity
            FROM cart c
            JOIN menu m ON c.dish_id = m.dish_id
            WHERE c.user_id = ?
        """, (user_id,))
        items = cursor.fetchall()

        # 3. Рассчитываем итоговую сумму
        total_amount = sum(item[2] * item[3] for item in items)

        # 4. Создаем запись о заказе
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO orders (user_id, order_date, total_amount, status)
            VALUES (?, ?, ?, ?)
        """, (user_id, order_date, total_amount, "принят"))
        order_id = cursor.lastrowid

        # 5. Добавляем позиции заказа
        for item in items:
            dish_id, name, price, quantity = item
            cursor.execute("""
                INSERT INTO order_items (order_id, dish_id, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (order_id, dish_id, quantity, price))

        # 6. Очищаем корзину
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        conn.commit()

        # 7. Формируем сообщение с подтверждением
        order_details = "✅ <b>Заказ оформлен!</b>\n\n"
        order_details += f"🆔 Номер: <code>#{order_id}</code>\n"
        order_details += f"📅 Дата: {order_date}\n"
        order_details += f"💵 Сумма: {total_amount}₽\n\n"
        order_details += "<b>Состав:</b>\n"

        for item in items:
            _, name, price, quantity = item
            order_details += f"• {name} × {quantity} — {price * quantity}₽\n"

        await callback.message.edit_text(
            order_details,
            reply_markup=None
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка оформления заказа: {e}")
        await callback.answer("⚠ Ошибка при оформлении заказа", show_alert=True)
        conn.rollback()
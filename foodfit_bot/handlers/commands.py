from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message
from datetime import datetime
from foodfit_bot.config.database import cursor, conn
from foodfit_bot.keyboards.reply import main_menu_kb
from foodfit_bot.models.states import Form
from foodfit_bot.services.database_service import is_admin

router = Router()

@router.message(Command("start"))
async def start_cmd(message: Message):
    """Обработчик команды /start"""
    user = message.from_user
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, registration_date) VALUES (?, ?, ?, ?)",
        (user.id, user.username, user.full_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

    await message.answer(
        "👋 Добро пожаловать в FoodFit!\nЯ помогу выбрать идеальное блюдо с учетом калорий!\nИспользуй команду /help",
        reply_markup=main_menu_kb()
    )

@router.message(Command("help"))
async def help_cmd(message: Message):
    """Обработчик команды /help"""
    text = (
        "🍽️ FoodFitBot PRO\n\n"
        "Команды:\n"
        "/menu - Показать меню\n"
        "/profile - Ваш профиль\n"
        "/cart - Корзина\n"
        "/filters - Фильтры меню\n"
        "/recommend - Персональная рекомендация\n\n"
        "Для персонала:\n"
        "/staff - Режим официанта\n"
        "/admin - Админ панель"
    )
    await message.answer(text)

@router.message(F.text == "🔙 Назад")
async def back_cmd(message: Message):
    """Обработчик кнопки 'Назад'"""
    await message.answer(
        "Главное меню",
        reply_markup=main_menu_kb()
    )

@router.message(Command("profile"))
async def profile_cmd(message: Message):
    """Обработчик команды /profile"""
    user_id = message.from_user.id

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, registration_date) VALUES (?, ?, ?, ?)",
        (user_id, message.from_user.username, message.from_user.full_name, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()

    cursor.execute("""
        SELECT u.full_name, u.diet_preferences, COUNT(o.order_id) 
        FROM users u
        LEFT JOIN orders o ON u.user_id = o.user_id
        WHERE u.user_id = ?
        GROUP BY u.user_id
    """, (user_id,))
    user = cursor.fetchone()

    text = f"""
👤 Ваш профиль

Имя: {user[0]}
Диета: {user[1] or 'не указана'}
Заказов: {user[2]}
    """
    await message.answer(text)

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Обработчик команды /admin"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен. Только для администраторов.")
        return

    from foodfit_bot.keyboards.reply import admin_kb  # Ленивый импорт для избежания циклических зависимостей
    await message.answer(
        "👨‍🍳 Панель администратора",
        reply_markup=admin_kb()
    )
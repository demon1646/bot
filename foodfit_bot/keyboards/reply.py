from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Основное меню для пользователей"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🍽 Меню"),
        KeyboardButton(text="🛒 Корзина")
    )
    builder.row(
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="⚙️ Фильтры")
    )
    return builder.as_markup(resize_keyboard=True)

def admin_kb() -> ReplyKeyboardMarkup:
    """Клавиатура администратора"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📝 Добавить блюдо"),
        KeyboardButton(text="📊 Список заказов")
    )
    builder.row(
        KeyboardButton(text="✏️ Редактировать блюдо"),
        KeyboardButton(text="❌ Удалить блюдо")
    )
    builder.row(
        KeyboardButton(text="👥 Режим официанта"),
        KeyboardButton(text="🔙 Выход")
    )
    return builder.as_markup(resize_keyboard=True)

def staff_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для персонала"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔍 Поиск блюда"),
        KeyboardButton(text="📊 Открытые заказы")
    )
    builder.row(
        KeyboardButton(text="✅ Завершить заказ"),
        KeyboardButton(text="🔄 Обновить список")
    )
    builder.row(
        KeyboardButton(text="🔙 Главное меню")
    )
    return builder.as_markup(resize_keyboard=True)

def filters_kb() -> ReplyKeyboardMarkup:
    """Клавиатура фильтров меню"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🥗 Веган"),
        KeyboardButton(text="🚫 Без глютена")
    )
    builder.row(
        KeyboardButton(text="🔙 Назад")
    )
    return builder.as_markup(resize_keyboard=True)

def cancel_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для отмены действий"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="❌ Отмена")
    )
    return builder.as_markup(resize_keyboard=True)

def skip_photo_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для пропуска загрузки фото"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="Пропустить")
    )
    return builder.as_markup(resize_keyboard=True)

def order_control_kb() -> ReplyKeyboardMarkup:
    """Клавиатура управления заказами"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Подтвердить"),
        KeyboardButton(text="❌ Отменить")
    )
    builder.row(
        KeyboardButton(text="🔄 Изменить статус")
    )
    return builder.as_markup(resize_keyboard=True)

def yes_no_kb() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Да"),
        KeyboardButton(text="❌ Нет")
    )
    return builder.as_markup(resize_keyboard=True)

def diet_preferences_kb() -> ReplyKeyboardMarkup:
    """Клавиатура выбора диетических предпочтений"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="Вегетарианская"),
        KeyboardButton(text="Веганская")
    )
    builder.row(
        KeyboardButton(text="Без глютена"),
        KeyboardButton(text="Кето")
    )
    builder.row(
        KeyboardButton(text="Нет предпочтений")
    )
    return builder.as_markup(resize_keyboard=True)
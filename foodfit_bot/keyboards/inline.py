from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_dish_keyboard(dish_id: int) -> InlineKeyboardMarkup:
    """
    Строит клавиатуру для блюда в меню
    :param dish_id: ID блюда
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔍 Подробнее",
            callback_data=f"dish_detail_{dish_id}"
        ),
        InlineKeyboardButton(
            text="➕ В корзину",
            callback_data=f"cart_{dish_id}"
        )
    )
    return builder.as_markup()


def build_cart_keyboard(items: list) -> InlineKeyboardMarkup:
    """
    Строит клавиатуру для корзины
    :param items: Список товаров в корзине
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    for item in items:
        dish_id = item['dish_id']
        name = item['name']

        builder.row(
            InlineKeyboardButton(
                text=f"❌ {name[:20]}",
                callback_data=f"remove_{dish_id}"
            ),
            InlineKeyboardButton(
                text="-",
                callback_data=f"decrease_{dish_id}"
            ),
            InlineKeyboardButton(
                text=str(item['quantity']),
                callback_data=f"quantity_{dish_id}"
            ),
            InlineKeyboardButton(
                text="+",
                callback_data=f"increase_{dish_id}"
            ),
            width=4
        )

    builder.row(
        InlineKeyboardButton(
            text="❌ Очистить корзину",
            callback_data="clear_cart"
        ),
        InlineKeyboardButton(
            text="✅ Оформить заказ",
            callback_data="checkout"
        ),
        width=2
    )

    return builder.as_markup()


def build_admin_dish_edit_kb() -> InlineKeyboardMarkup:
    """Клавиатура для выбора поля редактирования блюда"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Название", callback_data="editfield_name"),
        InlineKeyboardButton(text="Описание", callback_data="editfield_description")
    )
    builder.row(
        InlineKeyboardButton(text="Цену", callback_data="editfield_price"),
        InlineKeyboardButton(text="Калории", callback_data="editfield_calories")
    )
    builder.row(
        InlineKeyboardButton(text="Теги", callback_data="editfield_tags"),
        InlineKeyboardButton(text="Фото", callback_data="editfield_photo")
    )
    return builder.as_markup()


def build_delete_confirmation_kb(dish_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения удаления блюда
    :param dish_id: ID блюда для удаления
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да",
            callback_data=f"confirm_delete_{dish_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data="cancel_delete"
        )
    )
    return builder.as_markup()


def build_order_control_kb(order_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура управления заказом для персонала
    :param order_id: ID заказа
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Завершить",
            callback_data=f"complete_order_{order_id}"
        ),
        InlineKeyboardButton(
            text="📦 В доставку",
            callback_data=f"to_delivery_{order_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="ℹ️ Детали",
            callback_data=f"order_details_{order_id}"
        )
    )
    return builder.as_markup()


def build_filters_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура фильтров меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🥗 Веган", callback_data="filter_vegan"),
        InlineKeyboardButton(text="🚫 Без глютена", callback_data="filter_gluten_free")
    )
    builder.row(
        InlineKeyboardButton(text="🔥 Острое", callback_data="filter_spicy"),
        InlineKeyboardButton(text="🍗 Мясное", callback_data="filter_meat")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Сбросить фильтры", callback_data="filter_reset")
    )
    return builder.as_markup()


def build_pagination_keyboard(page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура пагинации
    :param page: Текущая страница
    :param total_pages: Всего страниц
    :param prefix: Префикс для callback_data
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    if page > 1:
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"{prefix}_page_{page - 1}"
        ))

    builder.add(InlineKeyboardButton(
        text=f"{page}/{total_pages}",
        callback_data="current_page"
    ))

    if page < total_pages:
        builder.add(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"{prefix}_page_{page + 1}"
        ))

    return builder.as_markup()
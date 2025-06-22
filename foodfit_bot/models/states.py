from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    """Класс состояний для добавления/редактирования блюд"""
    dish_name = State()
    dish_desc = State()
    dish_cal = State()
    dish_price = State()
    dish_photo = State()
    dish_tags = State()

    # Для системы обратной связи
    feedback_rating = State()
    feedback_comment = State()

    # Для работы с заказами
    waiting_for_order_id = State()
    order_editing = State()

    # Для поиска
    staff_search = State()

    # Для редактирования блюд
    waiting_for_dish = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_value = State()
    editing_dish = State()

    # Для работы с профилем
    editing_profile = State()
    changing_diet = State()

    # Для оплаты
    payment_method = State()
    payment_confirmation = State()

    # Для админ-панели
    admin_actions = State()

    # Для системы рекомендаций
    waiting_for_preferences = State()


class DeliveryStates(StatesGroup):
    """Состояния для оформления доставки"""
    waiting_address = State()
    waiting_time = State()
    waiting_contact = State()
    confirming_order = State()


class AdminStates(StatesGroup):
    """Специальные состояния для администраторов"""
    promo_creation = State()
    stats_period = State()
    mailing_content = State()


class UserProfileStates(StatesGroup):
    """Состояния для работы с профилем пользователя"""
    editing_name = State()
    editing_phone = State()
    editing_address = State()
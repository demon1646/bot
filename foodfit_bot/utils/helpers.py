import re
from datetime import datetime
from typing import Optional, Union, Dict, List
import logging

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    Очищает текст от лишних пробелов, переносов и HTML-тегов
    :param text: Исходный текст
    :return: Очищенный текст
    """
    if not text:
        return ""

    # Удаляем HTML-теги
    clean = re.sub(r'<[^>]+>', '', text)
    # Удаляем лишние пробелы и переносы
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Удаляем специальные символы (оставляем буквы, цифры и основные знаки препинания)
    clean = re.sub(r'[^\w\s.,!?а-яА-ЯёЁ\-]', '', clean)

    return clean


def validate_price(price_str: str) -> bool:
    """
    Проверяет, является ли строка корректной ценой
    :param price_str: Строка с ценой
    :return: bool
    """
    try:
        price = float(price_str)
        return price > 0
    except (ValueError, TypeError):
        return False


def format_order_date(date_str: str) -> str:
    """
    Форматирует дату заказа в удобочитаемый вид
    :param date_str: Дата в строковом формате из БД
    :return: Отформатированная строка с датой
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return date_obj.strftime("%d.%m.%Y в %H:%M")
    except (ValueError, TypeError):
        return date_str


def calculate_calories(dishes: List[Dict]) -> int:
    """
    Считает общее количество калорий в заказе
    :param dishes: Список блюд с их количеством
    :return: Суммарные калории
    """
    return sum(dish['calories'] * dish.get('quantity', 1) for dish in dishes)


def split_text(text: str, max_length: int = 4000) -> List[str]:
    """
    Разбивает длинный текст на части по max_length символов
    :param text: Исходный текст
    :param max_length: Максимальная длина части
    :return: Список частей текста
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        part = text[:max_length]
        # Ищем последний перенос строки или точку
        split_pos = max(
            part.rfind('\n'),
            part.rfind('. '),
            part.rfind('! '),
            part.rfind('? ')
        )

        if split_pos > 0:
            parts.append(text[:split_pos + 1])
            text = text[split_pos + 1:]
        else:
            parts.append(text[:max_length])
            text = text[max_length:]

    return parts


def extract_phone_number(text: str) -> Optional[str]:
    """
    Извлекает номер телефона из текста
    :param text: Текст, содержащий номер телефона
    :return: Номер телефона или None
    """
    phone_regex = r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    match = re.search(phone_regex, text)
    return match.group(0) if match else None


def format_dish_description(dish: Dict) -> str:
    """
    Форматирует описание блюда для вывода
    :param dish: Словарь с данными о блюде
    :return: Отформатированная строка
    """
    return (
        f"🍽 <b>{dish.get('name', 'Без названия')}</b>\n\n"
        f"📝 {dish.get('description', 'Нет описания')}\n\n"
        f"🔥 {dish.get('calories', 0)} ккал\n"
        f"💵 {dish.get('price', 0)}₽\n"
        f"🏷 Теги: {dish.get('tags', 'нет')}"
    )


def parse_time_input(time_str: str) -> Optional[datetime]:
    """
    Парсит введенное пользователем время
    :param time_str: Строка с временем (например, "18:30")
    :return: Объект datetime или None
    """
    try:
        hours, minutes = map(int, time_str.split(':'))
        if 0 <= hours < 24 and 0 <= minutes < 60:
            now = datetime.now()
            return now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    except (ValueError, AttributeError):
        return None


def calculate_delivery_time(address: str) -> int:
    """
    Рассчитывает примерное время доставки в минутах
    :param address: Адрес доставки
    :return: Время в минутах
    """
    # Простая реализация - можно подключить API карт для точного расчета
    base_time = 30
    additional_time = len(address) // 10  # Просто для примера
    return base_time + additional_time


def generate_order_summary(order: Dict) -> str:
    """
    Генерирует сводку по заказу
    :param order: Данные заказа
    :return: Форматированная строка
    """
    items_text = "\n".join(
        f"• {item['name']} × {item['quantity']} — {item['price'] * item['quantity']}₽"
        for item in order.get('items', [])
    )

    return (
        f"🆔 <b>Заказ #{order.get('order_id', '')}</b>\n"
        f"📅 {format_order_date(order.get('order_date', ''))}\n"
        f"💵 Итого: {order.get('total_amount', 0)}₽\n"
        f"📊 Статус: {order.get('status', 'неизвестен')}\n\n"
        f"<b>Состав:</b>\n{items_text}"
    )


def validate_email(email: str) -> bool:
    """
    Проверяет валидность email адреса
    :param email: Строка с email
    :return: bool
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
import sqlite3
import logging
from typing import Optional, List, Dict, Union, Tuple
from datetime import datetime
from foodfit_bot.config.config import ADMIN_IDS
from foodfit_bot.config.database import conn, cursor

logger = logging.getLogger(__name__)


class DatabaseService:
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        return user_id in ADMIN_IDS

    @staticmethod
    def add_user_if_not_exists(user_id: int, username: str, full_name: str) -> None:
        """Добавляет пользователя в БД, если его там нет"""
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username, full_name, registration_date) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления пользователя: {e}")

    @staticmethod
    def get_dish_info(dish_id: int) -> Optional[Dict]:
        """Возвращает информацию о блюде по ID"""
        try:
            cursor.execute(
                "SELECT name, description, price, calories, tags, photo FROM menu WHERE dish_id = ?",
                (dish_id,))
            dish = cursor.fetchone()
            if dish:
                return {
                    'name': dish[0],
                    'description': dish[1],
                    'price': dish[2],
                    'calories': dish[3],
                    'tags': dish[4],
                    'photo': dish[5]
                }
            return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения информации о блюде: {e}")
            return None

    @staticmethod
    def add_to_cart(user_id: int, dish_id: int) -> bool:
        """Добавляет блюдо в корзину пользователя"""
        try:
            # Проверяем, есть ли уже блюдо в корзине
            cursor.execute(
                "SELECT quantity FROM cart WHERE user_id = ? AND dish_id = ?",
                (user_id, dish_id))
            existing = cursor.fetchone()

            if existing:
                # Увеличиваем количество
                cursor.execute(
                    "UPDATE cart SET quantity = quantity + 1 WHERE user_id = ? AND dish_id = ?",
                    (user_id, dish_id))
            else:
                # Добавляем новую запись
                cursor.execute(
                    "INSERT INTO cart (user_id, dish_id, quantity) VALUES (?, ?, 1)",
                    (user_id, dish_id))

            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления в корзину: {e}")
            conn.rollback()
            return False

    @staticmethod
    def get_cart_contents(user_id: int) -> List[Dict]:
        """Возвращает содержимое корзины пользователя"""
        try:
            cursor.execute('''
                SELECT c.dish_id, m.name, m.price, c.quantity, m.calories 
                FROM cart c 
                JOIN menu m ON c.dish_id = m.dish_id 
                WHERE c.user_id = ?
            ''', (user_id,))
            return [{
                'dish_id': item[0],
                'name': item[1],
                'price': item[2],
                'quantity': item[3],
                'calories': item[4]
            } for item in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения корзины: {e}")
            return []

    @staticmethod
    def create_order(user_id: int, cart_items: List[Dict]) -> Optional[int]:
        """Создает заказ из содержимого корзины"""
        try:
            total = sum(item['price'] * item['quantity'] for item in cart_items)
            order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Создаем запись заказа
            cursor.execute(
                "INSERT INTO orders (user_id, order_date, total_amount, status) VALUES (?, ?, ?, ?)",
                (user_id, order_date, total, 'принят'))
            order_id = cursor.lastrowid

            # Добавляем элементы заказа
            for item in cart_items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, dish_id, quantity, price) VALUES (?, ?, ?, ?)",
                    (order_id, item['dish_id'], item['quantity'], item['price']))

            # Очищаем корзину
            cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
            conn.commit()
            return order_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка создания заказа: {e}")
            conn.rollback()
            return None

    @staticmethod
    def get_user_orders(user_id: int, limit: int = 5) -> List[Dict]:
        """Возвращает последние заказы пользователя"""
        try:
            cursor.execute('''
                SELECT o.order_id, o.order_date, o.total_amount, o.status 
                FROM orders o 
                WHERE o.user_id = ?
                ORDER BY o.order_date DESC
                LIMIT ?
            ''', (user_id, limit))
            return [{
                'order_id': order[0],
                'order_date': order[1],
                'total_amount': order[2],
                'status': order[3]
            } for order in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения заказов: {e}")
            return []

    @staticmethod
    def get_order_details(order_id: int) -> Optional[Dict]:
        """Возвращает детали заказа"""
        try:
            # Информация о заказе
            cursor.execute('''
                SELECT o.order_id, u.full_name, o.order_date, o.total_amount, o.status 
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                WHERE o.order_id = ?
            ''', (order_id,))
            order = cursor.fetchone()

            if not order:
                return None

            # Состав заказа
            cursor.execute('''
                SELECT m.name, oi.quantity, oi.price 
                FROM order_items oi
                JOIN menu m ON oi.dish_id = m.dish_id
                WHERE oi.order_id = ?
            ''', (order_id,))
            items = [{
                'name': item[0],
                'quantity': item[1],
                'price': item[2]
            } for item in cursor.fetchall()]

            return {
                'order_id': order[0],
                'customer_name': order[1],
                'order_date': order[2],
                'total_amount': order[3],
                'status': order[4],
                'items': items
            }
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения деталей заказа: {e}")
            return None

    @staticmethod
    def search_dishes(query: str, filters: Dict = None) -> List[Dict]:
        """Поиск блюд по названию и фильтрам"""
        try:
            base_query = "SELECT dish_id, name, price, calories FROM menu WHERE name LIKE ?"
            params = [f"%{query}%"]

            if filters:
                if 'vegan' in filters and filters['vegan']:
                    base_query += " AND tags LIKE '%веган%'"
                if 'gluten_free' in filters and filters['gluten_free']:
                    base_query += " AND (tags LIKE '%без глютена%' OR tags LIKE '%gluten free%')"

            base_query += " LIMIT 20"
            cursor.execute(base_query, params)

            return [{
                'dish_id': dish[0],
                'name': dish[1],
                'price': dish[2],
                'calories': dish[3]
            } for dish in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка поиска блюд: {e}")
            return []

    @staticmethod
    def update_dish(dish_id: int, field: str, value: Union[str, int]) -> bool:
        """Обновляет поле блюда"""
        try:
            cursor.execute(
                f"UPDATE menu SET {field} = ? WHERE dish_id = ?",
                (value, dish_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления блюда: {e}")
            conn.rollback()
            return False

    @staticmethod
    def get_user_preferences(user_id: int) -> Dict:
        """Возвращает предпочтения пользователя"""
        try:
            cursor.execute(
                "SELECT diet_preferences FROM users WHERE user_id = ?",
                (user_id,))
            preferences = cursor.fetchone()
            return {
                'diet': preferences[0] if preferences else None,
                'last_orders': DatabaseService.get_last_ordered_dishes(user_id)
            }
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения предпочтений: {e}")
            return {'diet': None, 'last_orders': []}

    @staticmethod
    def get_last_ordered_dishes(user_id: int, limit: int = 3) -> List[str]:
        """Возвращает последние заказанные блюда"""
        try:
            cursor.execute('''
                SELECT m.name 
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                JOIN menu m ON oi.dish_id = m.dish_id
                WHERE o.user_id = ?
                ORDER BY o.order_date DESC
                LIMIT ?
            ''', (user_id, limit))
            return [item[0] for item in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения истории заказов: {e}")
            return []

    @staticmethod
    def update_order_status(order_id: int, new_status: str) -> bool:
        """Обновляет статус заказа
        :param order_id: ID заказа
        :param new_status: Новый статус ('принят', 'готовится', 'завершен' и т.д.)
        :return: True если успешно, False если ошибка
        """
        try:
            cursor.execute(
                "UPDATE orders SET status = ? WHERE order_id = ?",
                (new_status, order_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления статуса заказа {order_id}: {e}")
            conn.rollback()
            return False

    @staticmethod
    def get_active_orders() -> List[Dict]:
        """Возвращает список активных заказов (статусы: 'принят', 'готовится', 'в доставке')
        :return: Список словарей с информацией о заказах
        """
        try:
            cursor.execute("""
                SELECT o.order_id, u.full_name, o.order_date, o.total_amount, o.status
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                WHERE o.status IN ('принят', 'готовится', 'в доставке')
                ORDER BY o.order_date DESC
            """)

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Ошибка получения активных заказов: {e}")
            return []


# Функции для быстрого доступа
def is_admin(*args, **kwargs):
    return DatabaseService.is_admin(*args, **kwargs)


def get_dish_info(*args, **kwargs):
    return DatabaseService.get_dish_info(*args, **kwargs)


def add_to_cart(*args, **kwargs):
    return DatabaseService.add_to_cart(*args, **kwargs)


def search_dishes(*args, **kwargs):
    return DatabaseService.search_dishes(*args, **kwargs)


def get_order_details(*args, **kwargs):
    return DatabaseService.get_order_details(*args, **kwargs)


def get_user_orders(*args, **kwargs):
    return DatabaseService.get_user_orders(*args, **kwargs)


def update_order_status(*args, **kwargs):
    return DatabaseService.update_order_status(*args, **kwargs)


def get_active_orders():
    return DatabaseService.get_active_orders()


def get_user_preferences(*args, **kwargs):
    return DatabaseService.get_user_preferences(*args, **kwargs)

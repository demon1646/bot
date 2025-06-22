import sqlite3
from foodfit_bot.config.config import BOT_TOKEN

conn = sqlite3.connect('foodfit.db')
cursor = conn.cursor()


def init_db():
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        diet_preferences TEXT,
        registration_date TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (
        dish_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        calories INTEGER,
        price INTEGER,
        photo TEXT,
        tags TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (
        cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        dish_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(dish_id) REFERENCES menu(dish_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_date TEXT,
        total_amount INTEGER,
        status TEXT DEFAULT 'new',
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        dish_id INTEGER,
        quantity INTEGER,
        price INTEGER,
        FOREIGN KEY(order_id) REFERENCES orders(order_id),
        FOREIGN KEY(dish_id) REFERENCES menu(dish_id)
    )''')

    conn.commit()

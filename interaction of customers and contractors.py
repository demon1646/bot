import telebot
from telebot import types

API_TOKEN = '7567273285:AAHVO5MGvt8uYoi5qenE2FiSgN_r1a5kmqg'
bot = telebot.TeleBot(API_TOKEN)

users_db = {}  # Словарь для хранения информации о пользователях
orders = {}  # Хранение заказов
responses = {}  # Хранение откликов подрядчиков


@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_customer = types.KeyboardButton("Я - заказчик")
    btn_contractor = types.KeyboardButton("Я - подрядчик")
    markup.add(btn_customer, btn_contractor)
    bot.send_message(message.chat.id, "Выберите вашу роль:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Я - заказчик")
def customer_mode(message):
    bot.send_message(message.chat.id, "Введите город:")
    bot.register_next_step_handler(message, process_city)


def process_city(message):
    city = message.text
    users_db[message.chat.id] = {'role': 'customer', 'city': city}
    bot.send_message(message.chat.id, f"Вы выбрали город {city}. Опишите услугу и укажите период выполнения работ (дд.мм - дд.мм):")
    bot.register_next_step_handler(message, process_order)


def process_order(message):
    order_description = message.text
    user_info = users_db[message.chat.id]
    orders[message.chat.id] = {'city': user_info['city'], 'description': order_description}
    bot.send_message(message.chat.id, "Ваш заказ зафиксирован. Ожидайте откликов от подрядчиков.")

    for contractor_id, contractor_data in users_db.items():
        if contractor_data['role'] == 'contractor' and contractor_data['city'] == user_info['city']:
            bot.send_message(contractor_id, f"Новый заказ в вашем городе: {order_description}")


@bot.message_handler(func=lambda message: message.text == "Я - подрядчик")
def contractor_mode(message):
    bot.send_message(message.chat.id, "Введите город:")
    bot.register_next_step_handler(message, process_contractor_city)


def process_contractor_city(message):
    city = message.text
    users_db[message.chat.id] = {'role': 'contractor', 'city': city}
    bot.send_message(message.chat.id, "Введите ваше имя и резюме (например, 'Василий, могу сделать, свободные даты, 5.000₽/день'):")
    bot.register_next_step_handler(message, process_contractor_resume)


def process_contractor_resume(message):
    resume = message.text
    contractor_data = users_db[message.chat.id]

    responses.setdefault(contractor_data['city'], []).append({'id': message.chat.id, 'resume': resume})
    bot.send_message(message.chat.id, "Ваш отклик зафиксирован. Ожидайте новые заказы.")

    for customer_id, customer_data in users_db.items():
        if customer_data['role'] == 'customer' and customer_data['city'] == contractor_data['city']:
            bot.send_message(customer_id, f"Отклик от подрядчика: {resume}")


bot.polling()

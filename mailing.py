import telebot
from telebot import types

# Замените 'YOUR_BOT_TOKEN' на ваш токен бота
API_TOKEN = '7129392041:AAEqxn-x9LiRXoqr8evgNNMmp5Q_zzUpcMA'
bot = telebot.TeleBot(API_TOKEN)

# Временное хранилище для ID канала/группы и сообщений
user_data = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! Нажмите кнопку ниже, чтобы начать рассылку сообщений.", reply_markup=start_keyboard())

def start_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_send = types.KeyboardButton("Начать рассылку")
    keyboard.add(button_send)
    return keyboard

@bot.message_handler(func=lambda message: message.text == "Начать рассылку")
def start_send(message):
    bot.reply_to(message, "Введите количество сообщений:")
    user_data[message.chat.id] = {'step': 'count'}

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'count')
def get_count(message):
    try:
        count = int(message.text)  # Получаем количество сообщений
        if count <= 0:
            bot.reply_to(message, "Количество сообщений должно быть положительным числом. Пожалуйста, введите снова:")
            return
        user_data[message.chat.id]['count'] = count
        user_data[message.chat.id]['step'] = 'text'
        bot.reply_to(message, "Введите текст сообщения:")
    except ValueError:
        bot.reply_to(message, "Пожалуйста, укажите корректное число.")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'text')
def get_text(message):
    user_data[message.chat.id]['text'] = message.text
    user_data[message.chat.id]['step'] = 'channel'
    bot.reply_to(message, "Введите ID канала/группы (например, @your_channel):")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'channel')
def get_channel(message):
    channel_id = message.text
    count = user_data[message.chat.id]['count']
    text = user_data[message.chat.id]['text']

    for _ in range(count):
        try:
            bot.send_message(channel_id, text)
            print(f"Сообщение отправлено в {channel_id}")
        except Exception as e:
            print(f"Не удалось отправить сообщение в {channel_id}: {e}")

    # Очистка данных пользователя после завершения
    del user_data[message.chat.id]
    bot.reply_to(message, f"Сообщение '{text}' отправлено в {channel_id} {count} раз(а).")

# Запускаем бота
bot.polling()

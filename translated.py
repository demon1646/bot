import telebot
import googletrans
from googletrans import Translator

LANGUAGES = googletrans.LANGUAGES

API_TOKEN = '7837589523:AAEVzgzUQyOh9gdvXTIljx4hMZ5RznO0GHQ'
bot = telebot.TeleBot(API_TOKEN)
translator = Translator()

user_languages = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "Добро пожаловать! Выберите язык для сообщений в канале:"
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for lang_code in LANGUAGES.keys():
        markup.add(LANGUAGES[lang_code])
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


@bot.message_handler(func=lambda message: True)
def set_language(message):
    if message.text in LANGUAGES.values():
        lang_code = list(LANGUAGES.keys())[list(LANGUAGES.values()).index(message.text)]
        user_languages[message.chat.id] = lang_code
        bot.send_message(message.chat.id, f"Выбранный язык: {message.text}")
        return
    if message.chat.id in user_languages:
        lang_code = user_languages[message.chat.id]
        translated_message = translator.translate(message.text, dest=lang_code).text
        bot.send_message(message.chat.id, translated_message)


# Запуск бота
if __name__ == '__main__':
    bot.polling()




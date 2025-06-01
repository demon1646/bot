import telebot
from telebot import types
from datetime import datetime
import json


bot = telebot.TeleBot('7584106218:AAGh5BVvAdsqtLi_WfBt7WOVszu3peKT4SU')


def get_schedule(day):
    with open('bibaboba.json', 'r', encoding='utf-8') as file:
        schedule = json.load(file)

    week_number = datetime.now().isocalendar()[1]
    week_type = 'znam' if week_number % 2 == 0 else 'chisl'

    return schedule[week_type].get(day, [])


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     'Привет, я бот для расписания. Выбери расписание какого дня ты хочешь узнать.\n'
                     'Monday - понедельник\n'
                     'Tuesday - вторник\n'
                     'Wednesday - среда\n'
                     'Thursday - четверг\n'
                     'Friday - пятница')
    show_buttons(message.chat.id)


def show_buttons(chat_id):
    markup = types.ReplyKeyboardMarkup()
    btn1 = types.KeyboardButton('Monday')
    btn2 = types.KeyboardButton('Tuesday')
    markup.row(btn1, btn2)
    btn3 = types.KeyboardButton('Wednesday')
    btn4 = types.KeyboardButton('Thursday')
    markup.row(btn3, btn4)
    btn5 = types.KeyboardButton('Friday')
    markup.row(btn5)
    bot.send_message(chat_id, "Нажмите на кнопку: ", reply_markup=markup)


@bot.message_handler(
    func=lambda message: message.text in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
def send_schedule(message):
    day = message.text
    schedule = get_schedule(day)
    if schedule:
        schedule_text = '\n'.join(schedule)
        bot.reply_to(message, f'Расписание на {day}:\n{schedule_text}')


bot.polling(none_stop=True)

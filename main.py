import telebot as tb
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

# Токены и ID из переменных окружения
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_GROUP_ID = os.getenv('ADMIN_GROUP_ID')

bot = tb.TeleBot(TOKEN)

# Состояния FSM
class States:
    START = 0
    SELECT_SERVICE = 1
    ENTER_NAME = 2
    ENTER_PHONE = 3
    SELECT_DATE = 4
    CONFIRM_BOOKING = 5

# Словарь для хранения данных пользователей
user_data = {}

# Клавиатуры
def create_main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Записаться на приём"))
    return markup

def create_services_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("Чистка зубов"),
        KeyboardButton("Пломбирование"),
        KeyboardButton("Удаление зуба"),
        KeyboardButton("Консультация")
    )
    return markup

def create_date_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("Сегодня"),
        KeyboardButton("Завтра"),
        KeyboardButton("Выбрать другую дату")
    )
    return markup

def create_time_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("10:00"),
        KeyboardButton("12:00"),
        KeyboardButton("14:00"),
        KeyboardButton("16:00")
    )
    return markup

def create_phone_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("Отправить номер", request_contact=True),
        KeyboardButton("Отмена")
    )
    return markup

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Привет! Я бот для записи на приём к стоматологу. Выберите действие:",
        reply_markup=create_main_menu_keyboard()
    )
    user_id = message.from_user.id
    user_data[user_id] = {}  # Создаём временный словарь для данных пользователя
    user_data[user_id]['state'] = States.START

# Обработка выбора услуги
@bot.message_handler(func=lambda message: message.text == "Записаться на приём")
def select_service(message):
    user_id = message.from_user.id
    user_data[user_id]['state'] = States.SELECT_SERVICE

    bot.send_message(
        message.chat.id,
        "Выберите услугу:",
        reply_markup=create_services_keyboard()
    )

# Обработка ввода данных
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('state') == States.SELECT_SERVICE)
def process_service(message):
    user_id = message.from_user.id
    user_data[user_id]['service'] = message.text
    user_data[user_id]['state'] = States.ENTER_NAME

    bot.send_message(
        message.chat.id,
        "Введите ваше имя:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Отмена"))
    )

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('state') == States.ENTER_NAME)
def process_name(message):
    if message.text == "Отмена":
        cancel_booking(message)
        return

    user_id = message.from_user.id
    user_data[user_id]['name'] = message.text
    user_data[user_id]['state'] = States.ENTER_PHONE

    bot.send_message(
        message.chat.id,
        "Отправьте ваш номер телефона:",
        reply_markup=create_phone_keyboard()
    )

@bot.message_handler(content_types=['contact'])
def process_contact(message):
    user_id = message.from_user.id

    if user_data.get(user_id, {}).get('state') == States.ENTER_PHONE:
        phone_number = message.contact.phone_number
        user_data[user_id]['phone'] = phone_number
        user_data[user_id]['state'] = States.SELECT_DATE

        bot.send_message(
            message.chat.id,
            f"Ваш номер телефона сохранён: {phone_number}",
            reply_markup=create_date_keyboard()
        )

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('state') == States.ENTER_PHONE)
def process_phone(message):
    if message.text == "Отмена":
        cancel_booking(message)
        return

    user_id = message.from_user.id
    user_data[user_id]['phone'] = message.text
    user_data[user_id]['state'] = States.SELECT_DATE

    bot.send_message(
        message.chat.id,
        "Выберите дату:",
        reply_markup=create_date_keyboard()
    )

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('state') == States.SELECT_DATE)
def process_date(message):
    user_id = message.from_user.id
    user_data[user_id]['date'] = message.text
    user_data[user_id]['state'] = States.CONFIRM_BOOKING

    bot.send_message(
        message.chat.id,
        "Выберите время:",
        reply_markup=create_time_keyboard()
    )

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('state') == States.CONFIRM_BOOKING)
def confirm_booking(message):
    user_id = message.from_user.id
    user_data[user_id]['time'] = message.text

    service = user_data[user_id]['service']
    name = user_data[user_id]['name']
    phone = user_data[user_id]['phone']
    date = user_data[user_id]['date']
    time = user_data[user_id]['time']

    confirmation_message = (
        f"Вы записаны на {service}:\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Дата: {date}\n"
        f"Время: {time}"
    )

    bot.send_message(
        message.chat.id,
        confirmation_message,
        reply_markup=create_main_menu_keyboard()
    )

    # Отправляем данные администратору
    admin_message = (
        f"Новая запись:\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Услуга: {service}\n"
        f"Дата: {date}\n"
        f"Время: {time}"
    )
    bot.send_message(ADMIN_GROUP_ID, admin_message)

    user_data[user_id]['state'] = States.START

# Отмена записи
def cancel_booking(message):
    user_id = message.from_user.id
    user_data[user_id]['state'] = States.START

    bot.send_message(
        message.chat.id,
        "Запись отменена.",
        reply_markup=create_main_menu_keyboard()
    )

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
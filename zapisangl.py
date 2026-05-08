import telebot
import sqlite3
import os
from telebot import apihelper

# если запускаю на pythonanywhere — включаю прокси
if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    apihelper.proxy = {'https': 'http://proxy.server:3128'}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bookings.db')

TOKEN = "8392920809:AAGefiopx9Pp2v79eKB8c2nEJmU1RXkJQv4"
bot = telebot.TeleBot(TOKEN)

# храню временные данные пользователя (пока он заполняет форму)
user_data = {}

# храню последнюю запись пользователя (чтобы можно было отменить)
user_last_booking = {}

services = {
    "pilling": "пилинг",
    "haircut": "стрижка",
    "manicure": "маникюр",
    "cleaning": "чистка лица"
}

MASTER_PROFILE = {
    "name": "Элвис",
    "description": "Мастер красоты 💅",
    "address": "Баку, центр",
    "phone": "+9940553007076"
}

time_slots = [
    "10:00", "12:00", "14:00", "16:00",
    "18:00", "19:00", "20:00", "21:00"
]

ADMIN_ID = 1438851138


# создаю таблицу если её нет
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            name TEXT,
            service TEXT,
            time TEXT
        )
    ''')
    conn.commit()
    conn.close()


@bot.message_handler(commands=["start"])
def start(message):
    init_db()
    bot.send_message(message.chat.id, "Привет! Введи своё имя:")
    bot.register_next_step_handler(message, client_name)


def client_name(message):
    name = message.text.strip()
    user_data[message.chat.id] = {"name": name}

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        telebot.types.InlineKeyboardButton("📋 Профиль мастера", callback_data="profile")
    )

    markup.row(
        telebot.types.InlineKeyboardButton("пилинг", callback_data="pilling"),
        telebot.types.InlineKeyboardButton("стрижка", callback_data="haircut")
    )

    markup.row(
        telebot.types.InlineKeyboardButton("маникюр", callback_data="manicure"),
        telebot.types.InlineKeyboardButton("чистка лица", callback_data="cleaning")
    )

    bot.send_message(
        message.chat.id,
        f"Приятно познакомиться, {name}! Выбери услугу:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    chat_id = call.message.chat.id

    # профиль мастера
    if call.data == "profile":
        text = (
            f"👤 {MASTER_PROFILE['name']}\n\n"
            f"{MASTER_PROFILE['description']}\n"
            f"📍 {MASTER_PROFILE['address']}\n"
            f"📞 {MASTER_PROFILE['phone']}"
        )

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton(
                "📩 Написать мастеру",
                url="https://t.me/jartloviy"
            )
        )

        bot.send_message(chat_id, text, reply_markup=markup)

    # выбор услуги
    elif call.data in services:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT time FROM bookings")
        taken = [row[0] for row in cur.fetchall()]
        conn.close()

        user_data[chat_id]["service"] = call.data
        available = [t for t in time_slots if t not in taken]

        if not available:
            bot.send_message(chat_id, "❌ Всё занято")
            return

        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for t in available:
            markup.add(telebot.types.InlineKeyboardButton(t, callback_data=f"time_{t}"))

        bot.send_message(chat_id, "⏰ Выбери время:", reply_markup=markup)

    # выбор времени
    elif call.data.startswith("time_"):
        time = call.data.replace("time_", "")

        if chat_id not in user_data:
            bot.send_message(chat_id, "Ошибка, напиши /start")
            return

        data = user_data[chat_id]
        name = data["name"]
        service_name = services.get(data["service"], data["service"])

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # проверка занятости
        cur.execute("SELECT * FROM bookings WHERE time = ?", (time,))
        if cur.fetchone():
            bot.send_message(chat_id, "⛔ Уже занято")
            conn.close()
            return

        # запись
        cur.execute(
            "INSERT INTO bookings (chat_id, name, service, time) VALUES (?, ?, ?, ?)",
            (chat_id, name, service_name, time)
        )
        conn.commit()
        conn.close()

        # запоминаю что записал
        user_last_booking[chat_id] = True

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton("❌ Отменить запись", callback_data="cancel")
        )

        bot.send_message(chat_id, f"✅ Ты записан на {service_name} в {time}", reply_markup=markup)

        # уведомление тебе
        try:
            bot.send_message(
                ADMIN_ID,
                f"📩 Новая запись\n👤 {name}\n💅 {service_name}\n⏰ {time}"
            )
        except:
            pass

        # очищаю временные данные
        del user_data[chat_id]

    # отмена записи
    elif call.data == "cancel":
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # удаляю запись именно этого пользователя
        cur.execute("SELECT * FROM bookings WHERE chat_id = ?", (chat_id,))
        record = cur.fetchone()

        if record:
            cur.execute("DELETE FROM bookings WHERE chat_id = ?", (chat_id,))
            conn.commit()
            bot.send_message(chat_id, "❌ Запись отменена")
        else:
            bot.send_message(chat_id, "У тебя нет записи")

        conn.close()

        if chat_id in user_last_booking:
            del user_last_booking[chat_id]


if __name__ == "__main__":
    print("Бот запущен")
    bot.polling(non_stop=True)
    

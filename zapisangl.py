import telebot
import sqlite3
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
# если запускаю на pythonanywhere — включаю прокси
if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    apihelper.proxy = {'https': 'http://proxy.server:3128'}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bookings.db')
ADMIN_ID =1438851138
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))


# храню временные данные пользователя (пока он заполняет форму)
MASTERS = {
    "1": {
        "name": "Elvin",

        "photo": "https://i.pinimg.com/736x/70/99/5c/70995c063dad8038584a8f8005f1aa7f.jpg",

        "bio": {
            "ru": "Барбер, мужские стрижки и борода.",
            "en": "Barber, men's haircuts and beard."
        },

        "services": {
            "haircut": {
                "ru": "Стрижка",
                "en": "Haircut"
            },

            "beard": {
                "ru": "Борода",
                "en": "Beard"
            }
        }
    },

    "2": {
        "name": "Emily",

        "photo": "https://i.pinimg.com/736x/1b/b3/54/1bb3549583422b850806233d67030c3f.jpg",

        "bio": {
            "ru": "Мастер маникюра и педикюра.",
            "en": "Manicure and pedicure specialist."
        },

        "services": {
            "manicure": {
                "ru": "Маникюр",
                "en": "Manicure"
            },

            "pedicure": {
                "ru": "Педикюр",
                "en": "Pedicure"
            }
        }
    }
}
MESSAGES = {
    "ru": {
        "start": "Привет! Введи своё имя:",
        "choose_master": "👤 Выбери мастера:",
        "choose_service": "💅 Выбери услугу:",
        "choose_date": "📅 Выбери дату:",
        "choose_time": "⏰ Выбери время:",
        "success": "✅ Ты записан!",
        "cancel": "❌ Отменить запись"
    },

    "en": {
    "start": "Hi! Enter your name:",
    "choose_master": "👤 Choose a master:",
    "choose_service": "💅 Choose a service:",
    "choose_date": "📅 Choose a date:",
    "choose_time": "⏰ Choose a time:",
    "success": "✅ Booking confirmed!",
    "cancel": "❌ Cancel booking"
}
    }

services = {
    "pilling":  "пилинг",
    "haircut":  "стрижка",
    "manicure": "маникюр",
    "cleaning": "чистка лица"
}
 
# Что показывать клиентам в профиле мастера
MASTER_PROFILE = {
    "name":        "Элвис",
    "description": "Мастер красоты 💅",
    "address":     "Баку, центр",
    "phone":       "+9940553007076"
}
 
# Все возможные временные слоты в течение дня
time_slots = [
    "10:00", "12:00", "14:00", "16:00",
    "18:00", "19:00", "20:00", "21:00"
]
 
# Временное хранилище пока клиент выбирает услугу/дату/время.
# Структура: { chat_id: {"name": "Аня", "service": "manicure", "date": "2025-05-06"} }
# Данные живут только пока бот работает — после перезапуска очищаются.
user_data = {}
 
 
# ╔══════════════════════════════════════════════════════════════╗
# ║  БАЗА ДАННЫХ                                                ║
# ╚══════════════════════════════════════════════════════════════╝
 
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Добавляем создание таблицы для записей
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        name TEXT,
        service TEXT,
        date TEXT,
        time TEXT
    )""")
    # Таблица для отзывов
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        master TEXT,
        rating INTEGER,
        review TEXT
    )""")
    conn.commit()
    conn.close()
 
 
def get_taken_slots(date: str) -> list:
    """
    Возвращает список уже занятых слотов на конкретную дату.
    Используется чтобы не показывать клиенту занятое время.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT time FROM bookings WHERE date = ?", (date,))
    taken = [row[0] for row in cur.fetchall()]
    conn.close()
    return taken
 
 
# ╔══════════════════════════════════════════════════════════════╗
# ║  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ                                    ║
# ╚══════════════════════════════════════════════════════════════╝
 
def get_days() -> list:
    """
    Возвращает список из 5 дат: сегодня + 4 дня вперёд.
    Формат: ["2025-05-05", "2025-05-06", ...]
    """
    today = datetime.now()
    return [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
 
 
def build_service_menu() -> telebot.types.InlineKeyboardMarkup:
    """
    Собирает меню выбора услуги.
    Кнопка профиля сверху, потом 2 колонки услуг.
    """
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("📋 Профиль мастера", callback_data="profile")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("пилинг",      callback_data="pilling"),
        telebot.types.InlineKeyboardButton("стрижка",     callback_data="haircut")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("маникюр",     callback_data="manicure"),
        telebot.types.InlineKeyboardButton("чистка лица", callback_data="cleaning")
    )
    return markup
 
 
# ╔══════════════════════════════════════════════════════════════╗
# ║  КОМАНДЫ КЛИЕНТА                                            ║
# ╚══════════════════════════════════════════════════════════════╝
 
@bot.message_handler(commands=["start"])
def start(message):

    init_db()

    markup = telebot.types.InlineKeyboardMarkup()

    markup.row(
        telebot.types.InlineKeyboardButton(
            "Русский 🇷🇺",
            callback_data="lang_ru"
        ),

        telebot.types.InlineKeyboardButton(
            "English 🇬🇧",
            callback_data="lang_en"
        )
    )

    bot.send_message(
        message.chat.id,
        "Выберите язык / Dil seçin:",
        reply_markup=markup
    )
    

def save_name(message):

    chat_id = message.chat.id

    user_data.setdefault(chat_id, {})
    user_data[chat_id]["name"] = message.text.strip()

    lang = user_data[chat_id].get("lang", "ru")

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    for master_id, master_data in MASTERS.items():

        markup.add(
            telebot.types.InlineKeyboardButton(
                master_data["name"],
                callback_data=f"master_{master_id}"
            )
        )

    bot.send_message(
        chat_id,
        MESSAGES[lang]["choose_master"],
        reply_markup=markup
    )            
        
# ╔══════════════════════════════════════════════════════════════╗
# ║  ОБРАБОТКА НАЖАТИЙ НА КНОПКИ (inline-кнопки)               ║
# ╚══════════════════════════════════════════════════════════════╝
def save_review(message):
    chat_id = message.chat.id
    review_text = message.text.strip()
    data = user_data.get(chat_id)
    
    if not data or "review_master" not in data:
        return

    master_id = data["review_master"]
    master_name = MASTERS[master_id]["name"]
    client_name = data.get("name", "Клиент")

    # Сохраняем в базу
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO reviews (name, master, rating, review) VALUES (?, ?, ?, ?)",
               (client_name, master_name, 5, review_text))
    conn.commit()
    conn.close()
    
    bot.send_message(chat_id, "⭐ Спасибо за ваш отзыв!")

    # УВЕДОМЛЕНИЕ ТЕБЕ (АДМИНУ)
    bot.send_message(ADMIN_ID, f"🔔 Новый отзыв!\n👤 От: {client_name}\n🧑‍🔧 Мастеру: {master_name}\n💬 Текст: {review_text}") 
@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    """
    Сюда попадают ВСЕ нажатия на inline-кнопки.
    call.data — это строка которую мы передали в callback_data при создании кнопки.
    Разбираем её и понимаем что нажал пользователь.
    """
    chat_id = call.message.chat.id
    
    # 1. ЯЗЫК
    if call.data.startswith("lang_"):
        lang = call.data.split("_")[1]
        user_data.setdefault(chat_id, {})
        user_data[chat_id]["lang"] = lang
        bot.send_message(chat_id, MESSAGES[lang]["start"])
        bot.register_next_step_handler(call.message, save_name)
        return

    # 2. ЗАЩИТА
    if chat_id not in user_data or "lang" not in user_data[chat_id]:
        bot.send_message(chat_id, "Данные потеряны. Нажмите /start")
        return

    lang = user_data[chat_id]["lang"]

    # 3. ВЫБОР МАСТЕРА
    if call.data.startswith("master_"):
        master_id = call.data.split("_")[1]
        user_data[chat_id]["master"] = master_id
        master_data = MASTERS[master_id]
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for service_key, service_data in master_data["services"].items():
            markup.add(telebot.types.InlineKeyboardButton(
                service_data[lang], callback_data=f"service_{service_key}"
            ))

        bot.send_photo(
            chat_id, 
            master_data["photo"], 
            caption=f"*{master_data['name']}*\n{master_data['bio'][lang]}\n\n{MESSAGES[lang]['choose_service']}",
            parse_mode="Markdown",
            reply_markup=markup
        )

    # 4. ВЫБОР УСЛУГИ
    elif call.data.startswith("service_"):
        user_data[chat_id]["service"] = call.data.split("_")[1]
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for d in get_days():
            markup.add(telebot.types.InlineKeyboardButton(d, callback_data=f"date_{d}"))
        bot.send_message(chat_id, MESSAGES[lang]["choose_date"], reply_markup=markup)

    # 5. ВЫБОР ДАТЫ
    elif call.data.startswith("date_"):
        date = call.data.replace("date_", "")
        user_data[chat_id]["date"] = date
        taken = get_taken_slots(date)
        available = [t for t in time_slots if t not in taken]

        if not available:
            bot.send_message(chat_id, f"😔 На {date} мест нет.")
            return

        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for t in available:
            markup.add(telebot.types.InlineKeyboardButton(t, callback_data=f"time_{t}"))
        bot.send_message(chat_id, MESSAGES[lang]["choose_time"], reply_markup=markup)

    # 6. ЗАПИСЬ И ВСЕ КНОПКИ (ОТМЕНА, ОТЗЫВ, ПЕРЕЗАПИСЬ)
    elif call.data.startswith("time_"):
        time = call.data.replace("time_", "")
        data = user_data.get(chat_id)
        name, date, master_id, service_key = data["name"], data["date"], data["master"], data["service"]
        service_name = MASTERS[master_id]["services"][service_key][lang]

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO bookings (chat_id, name, service, date, time) VALUES (?, ?, ?, ?, ?)",
                   (chat_id, name, service_name, date, time))
        conn.commit()
        conn.close()

        # Создаем ОДИН markup и добавляем все кнопки сразу
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton(MESSAGES[lang]["cancel"], callback_data=f"cancel_{date}_{time}"),
            telebot.types.InlineKeyboardButton("⭐ Оставить отзыв", callback_data=f"review_{master_id}"),
            telebot.types.InlineKeyboardButton("🔁 Записаться снова", callback_data="restart_booking")
        )

        bot.send_message(
            chat_id,
            f"{MESSAGES[lang]['success']}\n\n👤 Мастер: {MASTERS[master_id]['name']}\n💅 Услуга: {service_name}\n📅 {date}\n⏰ {time}",
            reply_markup=markup
        )
        
        try:
            bot.send_message(ADMIN_ID, f"📩 Новая запись!\n👤 {name}\n🧑‍🔧 {MASTERS[master_id]['name']}\n💅 {service_name}\n📅 {date}\n⏰ {time}")
        except: pass

    # 7. ОБРАБОТКА ОТЗЫВА
    elif call.data.startswith("review_"):
        user_data[chat_id]["review_master"] = call.data.split("_")[1]
        bot.send_message(chat_id, "Напиши отзыв одним сообщением:")
        bot.register_next_step_handler(call.message, save_review)

    # 8. ПЕРЕЗАПИСЬ
    elif call.data == "restart_booking":
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for m_id, m_data in MASTERS.items():
            markup.add(telebot.types.InlineKeyboardButton(m_data["name"], callback_data=f"master_{m_id}"))
        bot.send_message(chat_id, MESSAGES[lang]["choose_master"], reply_markup=markup)

    # 9. ОТМЕНА
    elif call.data.startswith("cancel_"):
        parts = call.data.split("_")
        if len(parts) == 3:
            date, time = parts[1], parts[2]
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("DELETE FROM bookings WHERE chat_id = ? AND date = ? AND time = ?", (chat_id, date, time))
            if cur.rowcount:
                bot.send_message(chat_id, f"❌ Запись на {date} {time} отменена.")
            conn.commit()
            conn.close()
# ╔══════════════════════════════════════════════════════════════╗
# ║  КОМАНДЫ МАСТЕРА (только для тебя)                          ║
# ╚══════════════════════════════════════════════════════════════╝
 
def is_admin(message) -> bool:
    """Проверяет что команду пишет именно мастер, а не кто попало."""
    return message.chat.id == ADMIN_ID
 
@bot.message_handler(commands=["clients"])
def show_clients(message):
    if not is_admin(message):
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT name, service, date, time
        FROM bookings
        WHERE chat_id != 0
        ORDER BY date, time
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "Пока нет клиентов.")
        return

    text = "📋 Список клиентов:\n\n"

    for i, row in enumerate(rows, start=1):
        name, service, date, time = row

        text += (
            f"{i}. 👤 {name}\n"
            f"💅 {service}\n"
            f"📅 {date}\n"
            f"⏰ {time}\n\n"
        )

    bot.send_message(message.chat.id, text)
@bot.message_handler(commands=["block"])
def block_slot(message):
    """
    /block — заблокировать слот (живая запись).
    Мастер вводит: 2025-05-06 14:00
    Бот записывает этот слот в базу как занятый — клиенты его не увидят.
    """
    if not is_admin(message):
        return  # молча игнорируем чужих
 
    bot.send_message(
        message.chat.id,
        "Введи дату и время которые нужно заблокировать.\n"
        "Формат: 2025-05-06 14:00"
    )
    bot.register_next_step_handler(message, do_block)
 
 
def do_block(message):
    """Получаем дату/время от мастера и блокируем слот."""
    try:
        parts = message.text.strip().split()
        date, time = parts[0], parts[1]
 
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
 
        # Проверяем что слот ещё свободен
        cur.execute("SELECT id FROM bookings WHERE date = ? AND time = ?", (date, time))
        if cur.fetchone():
            bot.send_message(message.chat.id, f"⚠️ Слот {date} {time} уже занят.")
            conn.close()
            return
 
        # chat_id = 0, name = "BLOCKED" — это наш маркер живой записи
        cur.execute(
            "INSERT INTO bookings (chat_id, name, service, date, time) VALUES (?, ?, ?, ?, ?)",
            (0, "BLOCKED", "живая запись", date, time)
        )
        conn.commit()
        conn.close()
 
        bot.send_message(message.chat.id, f"✅ Слот {date} в {time} заблокирован.")
 
    except (IndexError, ValueError):
        bot.send_message(
            message.chat.id,
            "Не понял формат. Попробуй так:\n2025-05-06 14:00"
        )
 
 
@bot.message_handler(commands=["unblock"])
def unblock_slot(message):
    """
    /unblock — разблокировать слот (живая запись отменилась).
    Мастер вводит: 2025-05-06 14:00
    Бот удаляет этот слот из базы — клиенты снова смогут его выбрать.
    """
    if not is_admin(message):
        return
 
    bot.send_message(
        message.chat.id,
        "Введи дату и время которые нужно разблокировать.\n"
        "Формат: 2025-05-06 14:00"
    )
    bot.register_next_step_handler(message, do_unblock)
 
 
def do_unblock(message):
    """Получаем дату/время от мастера и освобождаем слот."""
    try:
        parts = message.text.strip().split()
        date, time = parts[0], parts[1]
 
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Удаляем только заблокированные вручную (chat_id = 0)
        cur.execute(
            "DELETE FROM bookings WHERE chat_id = 0 AND date = ? AND time = ?",
            (date, time)
        )
        deleted = cur.rowcount
        conn.commit()
        conn.close()
 
        if deleted:
            bot.send_message(message.chat.id, f"✅ Слот {date} в {time} разблокирован.")
        else:
            bot.send_message(
                message.chat.id,
                "Не нашёл заблокированный вручную слот с такими датой/временем."
            )
 
    except (IndexError, ValueError):
        bot.send_message(
            message.chat.id,
            "Не понял формат. Попробуй так:\n2025-05-06 14:00"
        )
 
 
@bot.message_handler(commands=["schedule"])
def show_schedule(message):
    """
    /schedule — показать все записи на сегодня и завтра.
    Удобно чтобы мастер видел кто придёт.
    """
    if not is_admin(message):
        return
 
    today    = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
 
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT name, service, date, time FROM bookings WHERE date IN (?, ?) ORDER BY date, time",
        (today, tomorrow)
    )
    rows = cur.fetchall()
    conn.close()
 
    if not rows:
        bot.send_message(message.chat.id, "На сегодня и завтра записей нет.")
        return
 
    lines = ["📅 Записи на сегодня и завтра:\n"]
    for name, service, date, time in rows:
        label = "🔒 живая" if name == "BLOCKED" else f"👤 {name}"
        lines.append(f"{date} {time} — {label} ({service})")
 
    bot.send_message(message.chat.id, "\n".join(lines))
 
 
# ╔══════════════════════════════════════════════════════════════╗
# ║  ЗАПУСК БОТА                                                ║
# ╚══════════════════════════════════════════════════════════════╝
 
if __name__ == "__main__":
    print("Бот запущен ✅")
    bot.infinity_polling(skip_pending=True)
    # non_stop=True — бот перезапускается сам если упал из-за сети
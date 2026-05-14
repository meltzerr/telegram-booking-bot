import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command # ОБЯЗАТЕЛЬНО для работы /start

# Включаем логи, чтобы видеть в терминале, доходит ли сообщение
logging.basicConfig(level=logging.INFO)

# Используйте ваш НОВЫЙ токен от @BotFather
bot = Bot(token="8746006240:AAGZF5veHzbu8rsB4IWrDRT_9C0FpfgTTOE")
dp = Dispatcher()

# Исправленный декоратор
@dp.message(Command("start"))
async def start_command(message: types.Message):
    # Создаем клавиатуру правильно для 3.x
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="открыть веб страницу", web_app=types.WebAppInfo(url="https://meltzerr.github.io/telegram-booking-bot/"))]
        ],
        resize_keyboard=True
    )
    await message.answer("Привет! Нажми кнопку ниже.", reply_markup=markup)

async def main():
    # Удаляем старые сообщения, которые бот пропустил, пока был выключен
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
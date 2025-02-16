

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

bot = Bot('7723973774:AAHxO5XxnwbtJp7WQPs0JeQ0YVipgGe8IM8')
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Открыть регистрацию", web_app=types.WebAppInfo(url="https://sun4chek.github.io/host/"))]
        ],
        resize_keyboard=True
    )
    await message.answer("Нажмите кнопку для регистрации:", reply_markup=markup)

@dp.message()
async def handle_webapp_data(message: types.Message):
    try:
        data = message.text  # Получаем JSON с WebApp
        user_data = eval(data)  # Преобразуем в словарь (или используем json.loads())

        response = (
            f"✅ Новая регистрация!\n\n"
            f"👤 Имя: {user_data['name']}\n"
            f"📧 Email: {user_data['email']}\n"
            f"📱 Телефон: {user_data['phone']}"
        )

        await message.answer(response)
    except Exception as e:
        await message.answer("Ошибка обработки данных 😢")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())





import json
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
        if not message.text:
            await message.answer("Ошибка: нет данных 😢")
            return

        print(f"🔍 Данные от WebApp: {message.text}")  # Логируем данные

        user_data = json.loads(message.text)  # Безопасный разбор JSON

        response = (
            f"✅ Новая регистрация!\n\n"
            f"👤 Имя: {user_data.get('name', 'Не указано')}\n"
            f"📧 Email: {user_data.get('email', 'Не указано')}\n"
            f"📱 Телефон: {user_data.get('phone', 'Не указано')}"
        )

        await message.answer(response)

    except json.JSONDecodeError:
        await message.answer("Ошибка: получены некорректные данные 😢")
    except Exception as e:
        await message.answer(f"Ошибка обработки данных 😢\n\n{str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

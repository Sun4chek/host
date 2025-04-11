import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo

ADMIN_BOT_TOKEN = '7801444625:AAFsxR0p11GLhHg63SQXpSRq220dzvS7HoY'
bot = Bot(ADMIN_BOT_TOKEN)
dp = Dispatcher()

ALLOWED_ADMINS = {'2124333296'}

@dp.message(Command("start"))
async def start_command(message: types.Message):
    if str(message.from_user.id) not in ALLOWED_ADMINS:
        await message.answer("Доступ запрещен.")
        return

    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Управление меню", web_app=WebAppInfo(url="https://a1e9-77-123-251-59.ngrok-free.app/static/admin_webapp.html"))]
            # тут ссылка
        ],
        resize_keyboard=True
    )
    await message.answer("Введите уникальный код ресторана или откройте управление меню:", reply_markup=markup)

@dp.message()
async def handle_webapp_data(message: types.Message):
    if str(message.from_user.id) not in ALLOWED_ADMINS:
        await message.answer("Доступ запрещен.")
        return

    try:
        if not message.web_app_data:
            await message.answer("Ошибка: WebApp не передал данные 😢")
            return

        data = json.loads(message.web_app_data.data)
        action = data.get('action')

        if action == 'add':
            await bot.send_message(message.from_user.id, f"Добавлено блюдо: {data['name']}")
        elif action == 'update':
            await bot.send_message(message.from_user.id, f"Обновлено блюдо: {data['name']}")
        elif action == 'delete':
            await bot.send_message(message.from_user.id, f"Удалено блюдо: {data['name']}")
        elif action == 'stop_list':
            await bot.send_message(message.from_user.id, f"Блюдо {data['name']} добавлено/удалено из стоп-листа")

    except json.JSONDecodeError:
        await message.answer("Ошибка: получены некорректные данные 😢")
    except Exception as e:
        await message.answer(f"Ошибка обработки данных 😢\n\n{str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
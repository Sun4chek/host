


#
# import json
# from aiogram import Bot, Dispatcher, types
# from aiogram.filters import Command
#
# ADMIN_ID = "1948431948"
# bot = Bot('7723973774:AAHxO5XxnwbtJp7WQPs0JeQ0YVipgGe8IM8')
# dp = Dispatcher()
#
# @dp.message(Command("start"))
# async def start_command(message: types.Message):
#     markup = types.ReplyKeyboardMarkup(
#         keyboard=[
#             [types.KeyboardButton(text="Открыть регистрацию", web_app=types.WebAppInfo(url="https://sun4chek.github.io/host/"))]
#         ],
#         resize_keyboard=True
#     )
#     await message.answer("Нажмите кнопку для регистрации:", reply_markup=markup)
#
# @dp.message()
# async def handle_webapp_data(message: types.Message):
#     try:
#         if not message.web_app_data:
#             await message.answer("Ошибка: WebApp не передал данные 😢")
#             return
#
#         print(f"🔍 Данные от WebApp: {message.web_app_data.data}")  # Логируем данные
#
#         user_data = json.loads(message.web_app_data.data)
#
#         response = (
#             f"✅ Новая регистрация!\n\n"
#             f"👤 Имя: {user_data.get('name', 'Не указано')}\n"
#             f"📧 Email: {user_data.get('email', 'Не указано')}\n"
#             f"📱 Телефон: {user_data.get('phone', 'Не указано')}"
#         )
#
#         await message.answer(response)
#         await bot.send_message(ADMIN_ID, f"📩 Новая регистрация:\n\n{response}")
#
#     except json.JSONDecodeError:
#         await message.answer("Ошибка: получены некорректные данные 😢")
#     except Exception as e:
#         await message.answer(f"Ошибка обработки данных 😢\n\n{str(e)}")
#
#
# async def main():
#     await dp.start_polling(bot)
#
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())


import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

ADMIN_ID = "1948431948"
bot = Bot('7723973774:AAHxO5XxnwbtJp7WQPs0JeQ0YVipgGe8IM8')
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Открыть меню", web_app=types.WebAppInfo(url="https://sun4chek.github.io/host/"))]
        ],
        resize_keyboard=True
    )
    await message.answer("Нажмите кнопку для открытия меню:", reply_markup=markup)

@dp.message()
async def handle_webapp_data(message: types.Message):
    try:
        if not message.web_app_data:
            await message.answer("Ошибка: WebApp не передал данные 😢")
            return

        print(f"🔍 Данные от WebApp: {message.web_app_data.data}")  # Логируем данные

        # Парсим JSON-объект
        user_data = json.loads(message.web_app_data.data)

        # Формируем сообщение для пользователя
        response = (
            f"✅ Новый заказ!\n\n"
            f"👤 Фамилия: {user_data.get('lastName', 'Не указано')}\n"
            f"👤 Имя: {user_data.get('firstName', 'Не указано')}\n"
            f"📱 Телефон: {user_data.get('phone', 'Не указано')}\n"
            f"💳 Способ оплаты: {user_data.get('paymentMethod', 'Не указано')}\n"
            f"🚚 Способ получения: {user_data.get('deliveryMethod', 'Не указано')}\n"
            f"🏠 Номер комнаты: {user_data.get('roomNumber', 'Не указано')}\n\n"
            f"🍽 Заказанные блюда:\n"
        )

        # Добавляем список блюд
        for item in user_data.get('cart', []):
            response += f"- {item['name']} - {item['price']}₽\n"

        response += f"\n💸 Итого: {user_data.get('total', '0')}₽"

        # Отправляем сообщение пользователю
        await message.answer(response)

        # Отправляем уведомление администратору
        await bot.send_message(ADMIN_ID, f"📩 Новый заказ:\n\n{response}")

    except json.JSONDecodeError:
        await message.answer("Ошибка: получены некорректные данные 😢")
    except Exception as e:
        await message.answer(f"Ошибка обработки данных 😢\n\n{str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
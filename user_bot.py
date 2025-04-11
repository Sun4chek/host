import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

ADMIN_ID = "1948431948"
bot = Bot('7490268639:AAHdO3Ehmhc_I__gZ_ixU_SQ1Nx61q13sfA')
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Открыть меню", web_app=types.WebAppInfo(url="https://a1e9-77-123-251-59.ngrok-free.app/static/user_webapp.html"))]
        #тут ссылка



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

        print(f"🔍 Данные от WebApp: {message.web_app_data.data}")
        order_data = json.loads(message.web_app_data.data)

        customer = order_data['customer']
        order_details = order_data['orderDetails']

        response = (
            f"✅ Новый заказ!\n\n"
            f"👤 Фамилия: {customer['lastName']}\n"
            f"👤 Имя: {customer['firstName']}\n"
            f"📱 Телефон: {customer['phone']}\n"
            f"💳 Способ оплаты: {order_details['paymentMethod']}\n"
            f"🚚 Способ получения: {order_details['deliveryMethod']}\n"
            f"🏠 Номер комнаты: {customer['roomNumber']}\n\n"
            f"🍽 Заказанные блюда:\n"
        )

        for item in order_details['items']:
            response += f"- {item['name']} ({item['quantity']} шт.) - {item['price']}₽\n"

        response += f"\n💸 Итого: {order_details['total']}₽\n"
        if any(item.get('isAlcohol', False) for item in order_details['items']):
            response += f"ℹ️ {order_details['alcoholNote']}"

        # Отправка пользователю
        await message.answer(response)
        # Отправка администратору
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
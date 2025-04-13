import json
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import WebAppInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
USER_BOT_TOKEN = os.getenv("USER_BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://buhtarest-webhook.onrender.com")
ALLOWED_ADMINS = set(os.getenv("ALLOWED_ADMINS", "").split(","))
PORT = int(os.getenv("WEBHOOK_PORT", 8001))
API_BASE_URL = os.getenv("API_BASE_URL", "https://buhtarest-api.onrender.com")

# Инициализация ботов
user_bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)
user_dp = Dispatcher()
admin_dp = Dispatcher()

# Обработчики основного бота
@user_dp.message(Command("start"))
async def start_command_user(message: types.Message):
    logger.debug(f"Получена команда /start от пользователя {message.from_user.id}")
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(
                text="Открыть меню",
                web_app=WebAppInfo(url=f"{API_BASE_URL}/static/user_webapp.html")
            )]
        ],
        resize_keyboard=True
    )
    await message.answer("Нажмите кнопку для открытия меню:", reply_markup=markup)

@user_dp.message()
async def handle_webapp_data_user(message: types.Message):
    logger.debug(f"Получены WebApp данные от пользователя {message.from_user.id}")
    try:
        if not message.web_app_data:
            logger.error("WebApp не передал данные")
            await message.answer("Ошибка: WebApp не передал данные 😢")
            return

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

        await message.answer(response)
        for admin_id in ALLOWED_ADMINS:
            await user_bot.send_message(admin_id, f"📩 Новый заказ:\n\n{response}")

    except json.JSONDecodeError:
        logger.error("Некорректные JSON данные от WebApp")
        await message.answer("Ошибка: получены некорректные данные 😢")
    except Exception as e:
        logger.error(f"Ошибка обработки WebApp данных: {e}")
        await message.answer(f"Ошибка обработки данных 😢\n\n{str(e)}")

# Обработчики админского бота
@admin_dp.message(Command("start"))
async def start_command_admin(message: types.Message):
    logger.debug(f"Получена команда /start от админа {message.from_user.id}")
    if str(message.from_user.id) not in ALLOWED_ADMINS:
        await message.answer("Доступ запрещен.")
        return

    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(
                text="Управление меню",
                web_app=WebAppInfo(url=f"{API_BASE_URL}/static/admin_webapp.html")
            )]
        ],
        resize_keyboard=True
    )
    await message.answer("Введите уникальный код ресторана или откройте управление меню:", reply_markup=markup)

@admin_dp.message()
async def handle_webapp_data_admin(message: types.Message):
    logger.debug(f"Получены WebApp данные от админа {message.from_user.id}")
    if str(message.from_user.id) not in ALLOWED_ADMINS:
        await message.answer("Доступ запрещен.")
        return

    try:
        if not message.web_app_data:
            logger.error("WebApp не передал данные")
            await message.answer("Ошибка: WebApp не передал данные 😢")
            return

        data = json.loads(message.web_app_data.data)
        action = data.get('action')

        if action == 'add':
            await admin_bot.send_message(message.from_user.id, f"Добавлено блюдо: {data['name']}")
        elif action == 'update':
            await admin_bot.send_message(message.from_user.id, f"Обновлено блюдо: {data['name']}")
        elif action == 'delete':
            await admin_bot.send_message(message.from_user.id, f"Удалено блюдо: {data['name']}")
        elif action == 'stop_list':
            await admin_bot.send_message(message.from_user.id, f"Блюдо {data['name']} добавлено/удалено из стоп-листа")

    except json.JSONDecodeError:
        logger.error("Некорректные JSON данные от WebApp")
        await message.answer("Ошибка: получены некорректные данные 😢")
    except Exception as e:
        logger.error(f"Ошибка обработки WebApp данных: {e}")
        await message.answer(f"Ошибка обработки данных 😢\n\n{str(e)}")

# Webhook настройка
async def on_startup(app):
    logger.debug(f"Запуск настройки вебхуков с BASE_URL: {BASE_URL}")
    webhook_path_user = "/webhook/user"
    webhook_path_admin = "/webhook/admin"
    try:
        await user_bot.set_webhook(f"{BASE_URL}{webhook_path_user}")
        await admin_bot.set_webhook(f"{BASE_URL}{webhook_path_admin}")
        logger.debug(f"Webhooks установлены: {BASE_URL}{webhook_path_user}, {BASE_URL}{webhook_path_admin}")
    except Exception as e:
        logger.error(f"Ошибка установки вебхуков: {e}")
    logger.debug(f"Сервер запускается на порту: {PORT}")

async def on_shutdown(app):
    logger.debug("Удаление вебхуков")
    try:
        await user_bot.delete_webhook()
        await admin_bot.delete_webhook()
        await user_bot.session.close()
        await admin_bot.session.close()
        logger.debug("Webhooks удалены")
    except Exception as e:
        logger.error(f"Ошибка удаления вебхуков: {e}")

# Aiohttp приложение
aiohttp_app = web.Application()
user_handler = SimpleRequestHandler(dispatcher=user_dp, bot=user_bot)
admin_handler = SimpleRequestHandler(dispatcher=admin_dp, bot=admin_bot)
user_handler.register(aiohttp_app, path="/webhook/user")
admin_handler.register(aiohttp_app, path="/webhook/admin")
setup_application(aiohttp_app, user_dp, bot=user_bot)
setup_application(aiohttp_app, admin_dp, bot=admin_bot)

# Регистрация хуков
aiohttp_app.on_startup.append(on_startup)
aiohttp_app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    logger.debug(f"Запуск aiohttp на порту {PORT}")
    web.run_app(aiohttp_app, host="0.0.0.0", port=PORT)
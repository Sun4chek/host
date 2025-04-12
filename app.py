import json
import os
import sqlite3
import logging
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO
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
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5001")
ALLOWED_ADMINS = set(os.getenv("ALLOWED_ADMINS", "").split(","))
DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'restaurant.db')

# Инициализация Flask и SocketIO
flask_app = Flask(__name__, static_folder='static')
socketio = SocketIO(flask_app, async_mode='eventlet', cors_allowed_origins="*")

# Инициализация ботов
user_bot = Bot(token=USER_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)
user_dp = Dispatcher()
admin_dp = Dispatcher()

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Функция для получения меню
def fetch_menu_data(restaurant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM MenuCategories WHERE restaurant_id = ?', (restaurant_id,))
    categories = cursor.fetchall()

    menu_data = {}
    for category in categories:
        cursor.execute('''
            SELECT id, name, portion_price, bottle_price, weight, image, description, is_alcohol, in_stop_list
            FROM MenuItems WHERE category_id = ?
        ''', (category['id'],))
        items = cursor.fetchall()
        menu_data[category['name']] = [
            {
                "id": item['id'],
                "name": item['name'],
                "portion_price": item['portion_price'],
                "bottle_price": item['bottle_price'],
                "weight": item['weight'],
                "image": item['image'] or f"{BASE_URL}/static/images/placeholder.jpg",
                "description": item['description'],
                "is_alcohol": bool(item['is_alcohol']),
                "in_stop_list": bool(item['in_stop_list'])
            } for item in items
        ]
    conn.close()
    return menu_data

# Flask API маршруты
@flask_app.route('/api/menu/<restaurant_code>', methods=['GET'])
def get_menu(restaurant_code):
    logger.debug(f"Запрос меню для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        menu_data = fetch_menu_data(restaurant_id)
        conn.close()
        return jsonify(menu_data)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/menu/<restaurant_code>', methods=['POST'])
def add_menu_item(restaurant_code):
    logger.debug(f"Добавление позиции в меню для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        data = request.get_json()

        cursor.execute('SELECT id FROM MenuCategories WHERE name = ? AND restaurant_id = ?',
                       (data['category'], restaurant_id))
        category = cursor.fetchone()
        if not category:
            cursor.execute('INSERT INTO MenuCategories (name, restaurant_id) VALUES (?, ?)',
                           (data['category'], restaurant_id))
            category_id = cursor.lastrowid
        else:
            category_id = category['id']

        cursor.execute('''
            INSERT INTO MenuItems (category_id, name, portion_price, bottle_price, weight, image, description, is_alcohol, in_stop_list)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (category_id, data['name'], data['portion_price'], data['bottle_price'],
              data['weight'], data['image'], data['description'], data['is_alcohol'], data['in_stop_list']))

        conn.commit()
        menu_data = fetch_menu_data(restaurant_id)
        socketio.emit('menu_updated', menu_data)
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/menu/<restaurant_code>/<int:item_id>', methods=['PUT'])
def update_menu_item(restaurant_code, item_id):
    logger.debug(f"Обновление позиции {item_id} для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        data = request.get_json()

        cursor.execute('SELECT id FROM MenuCategories WHERE name = ? AND restaurant_id = ?',
                       (data['category'], restaurant_id))
        category = cursor.fetchone()
        if not category:
            cursor.execute('INSERT INTO MenuCategories (name, restaurant_id) VALUES (?, ?)',
                           (data['category'], restaurant_id))
            category_id = cursor.lastrowid
        else:
            category_id = category['id']

        cursor.execute('''
            UPDATE MenuItems 
            SET category_id = ?, name = ?, portion_price = ?, bottle_price = ?, weight = ?, 
                image = ?, description = ?, is_alcohol = ?, in_stop_list = ?
            WHERE id = ?
        ''', (category_id, data['name'], data['portion_price'], data['bottle_price'],
              data['weight'], data['image'], data['description'], data['is_alcohol'],
              data['in_stop_list'], item_id))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Позиция не найдена"}), 404

        conn.commit()
        menu_data = fetch_menu_data(restaurant_id)
        socketio.emit('menu_updated', menu_data)
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/menu/<restaurant_code>/<int:item_id>', methods=['DELETE'])
def delete_menu_item(restaurant_code, item_id):
    logger.debug(f"Удаление позиции {item_id} для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        cursor.execute('DELETE FROM MenuItems WHERE id = ?', (item_id,))
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Позиция не найдена"}), 404

        conn.commit()
        menu_data = fetch_menu_data(restaurant_id)
        socketio.emit('menu_updated', menu_data)
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/orders/<restaurant_code>', methods=['GET'])
def get_orders(restaurant_code):
    logger.debug(f"Получение заказов для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        cursor.execute('''
            SELECT id, last_name, first_name, phone, payment_method, delivery_method, room_number, total, timestamp
            FROM Orders WHERE restaurant_id = ?
            ORDER BY timestamp DESC
        ''', (restaurant_id,))
        orders = cursor.fetchall()

        orders_data = []
        for order in orders:
            cursor.execute('''
                SELECT item_id, name, price, quantity, is_alcohol
                FROM OrderItems WHERE order_id = ?
            ''', (order['id'],))
            items = cursor.fetchall()
            orders_data.append({
                "id": order['id'],
                "customer": {
                    "last_name": order['last_name'],
                    "first_name": order['first_name'],
                    "phone": order['phone'],
                    "room_number": order['room_number']
                },
                "order_details": {
                    "payment_method": order['payment_method'],
                    "delivery_method": order['delivery_method'],
                    "items": [
                        {
                            "item_id": item['item_id'],
                            "name": item['name'],
                            "price": item['price'],
                            "quantity": item['quantity'],
                            "is_alcohol": bool(item['is_alcohol'])
                        } for item in items
                    ],
                    "total": order['total'],
                    "timestamp": order['timestamp']
                }
            })

        conn.close()
        return jsonify(orders_data)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/order/<restaurant_code>', methods=['POST'])
def add_order(restaurant_code):
    logger.debug(f"Добавление заказа для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            logger.error(f"Ресторан с кодом {restaurant_code} не найден")
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        data = request.get_json()

        if not data.get('customer') or not data.get('orderDetails'):
            logger.error("Отсутствуют customer или orderDetails")
            conn.close()
            return jsonify({"error": "Некорректные данные заказа"}), 400

        customer = data['customer']
        order_details = data['orderDetails']

        total = float(order_details['total'])
        cursor.execute('''
            INSERT INTO Orders (restaurant_id, last_name, first_name, phone, payment_method, delivery_method, room_number, total, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (restaurant_id, customer['lastName'], customer['firstName'], customer['phone'],
              order_details['paymentMethod'], order_details['deliveryMethod'], customer['roomNumber'],
              total, data['timestamp']))

        order_id = cursor.lastrowid
        for item in order_details['items']:
            cursor.execute('''
                INSERT INTO OrderItems (order_id, item_id, name, price, quantity, is_alcohol)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, item.get('item_id'), item['name'], float(item['price']), item['quantity'], item.get('isAlcohol', False)))

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "order_id": order_id}), 200
    except ValueError as ve:
        logger.error(f"Ошибка преобразования данных: {ve}")
        conn.close()
        return jsonify({"error": f"Ошибка данных: {ve}"}), 400
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/static/<path:path>')
def serve_static(path):
    logger.debug(f"Запрос статического файла: {path}")
    return send_from_directory('static', path)

# Aiohttp для webhook’ов
aiohttp_app = web.Application()
user_handler = SimpleRequestHandler(dispatcher=user_dp, bot=user_bot)
admin_handler = SimpleRequestHandler(dispatcher=admin_dp, bot=admin_bot)
user_handler.register(aiohttp_app, path="/webhook/user")
admin_handler.register(aiohttp_app, path="/webhook/admin")
setup_application(aiohttp_app, user_dp, bot=user_bot)
setup_application(aiohttp_app, admin_dp, bot=admin_bot)

# Webhook настройка
async def on_startup(_):
    logger.debug(f"Запуск настройки вебхуков с BASE_URL: {BASE_URL}")
    webhook_path_user = "/webhook/user"
    webhook_path_admin = "/webhook/admin"
    await user_bot.set_webhook(f"{BASE_URL}{webhook_path_user}")
    await admin_bot.set_webhook(f"{BASE_URL}{webhook_path_admin}")
    logger.debug(f"Webhooks установлены: {BASE_URL}{webhook_path_user}, {BASE_URL}{webhook_path_admin}")

async def on_shutdown(_):
    logger.debug("Удаление вебхуков")
    await user_bot.delete_webhook()
    await admin_bot.delete_webhook()
    await user_bot.session.close()
    await admin_bot.session.close()
    logger.debug("Webhooks удалены")

aiohttp_app.on_startup.append(on_startup)
aiohttp_app.on_shutdown.append(on_shutdown)

# Обработчики основного бота
@user_dp.message(Command("start"))
async def start_command_user(message: types.Message):
    logger.debug(f"Получена команда /start от пользователя {message.from_user.id}")
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(
                text="Открыть меню",
                web_app=WebAppInfo(url=f"{BASE_URL}/static/user_webapp.html")
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
                web_app=WebAppInfo(url=f"{BASE_URL}/static/admin_webapp.html")
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

if __name__ == "__main__":
    logger.debug("Запуск в локальном режиме")
    socketio.run(flask_app, host="0.0.0.0", port=5001, debug=True)
else:
    logger.debug("Запуск в продакшен-режиме")
    # Добавляем aiohttp маршруты в Flask приложение
    flask_app.aiohttp_app = aiohttp_app
    try:
        from eventlet import wsgi
        import eventlet
        wsgi.server(eventlet.listen(('', 5001)), flask_app)
        logger.debug("Flask с aiohttp запущен через eventlet")
    except ImportError:
        logger.error("Ошибка: eventlet не установлен. Установите с помощью 'pip install eventlet'.")
        raise
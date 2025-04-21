import json
import os
import psycopg2
import logging
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv('.env.main')

# Конфигурация
BASE_URL = os.getenv("BASE_URL", "https://buhtarest-api.onrender.com")
DATABASE_URL = os.getenv("DATABASE_URL")

# Проверка DATABASE_URL
if not DATABASE_URL:
    logger.error("DATABASE_URL не установлен в переменных окружения")
    raise Exception("DATABASE_URL required")

# Инициализация Flask
flask_app = Flask(__name__)
CORS(flask_app, resources={r"/api/*": {"origins": "*"}})

# Подключение к базе данных
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        raise

# Функция для получения меню
def fetch_menu_data(restaurant_id):
    logger.debug(f"Получение меню для restaurant_id: {restaurant_id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM MenuCategories WHERE restaurant_id = %s', (restaurant_id,))
        categories = cursor.fetchall()

        menu_data = {}
        for category in categories:
            cursor.execute('''
                SELECT id, name, portion_price, bottle_price, weight, image, description, is_alcohol, in_stop_list
                FROM MenuItems WHERE category_id = %s
            ''', (category['id'],))
            items = cursor.fetchall()
            menu_data[category['name']] = [
                {
                    "id": item['id'],
                    "name": item['name'],
                    "portion_price": float(item['portion_price']) if item['portion_price'] is not None else None,
                    "bottle_price": float(item['bottle_price']) if item['bottle_price'] is not None else None,
                    "weight": item['weight'],
                    "image": item['image'] or f"{BASE_URL}/static/images/placeholder.jpg",
                    "description": item['description'],
                    "is_alcohol": item['is_alcohol'],
                    "in_stop_list": item['in_stop_list']
                } for item in items
            ]
        conn.close()
        logger.debug(f"Меню: {json.dumps(menu_data, ensure_ascii=False)}")
        return menu_data
    except Exception as e:
        logger.error(f"Ошибка получения меню: {e}")
        raise

# Flask API маршруты
@flask_app.route('/api/menu/<restaurant_code>', methods=['GET'])
def get_menu(restaurant_code):
    logger.info(f"Запрос меню для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = %s', (restaurant_code,))
        restaurant = cursor.fetchone()
        logger.debug(f"Ресторан: {restaurant}")
        if not restaurant:
            conn.close()
            logger.warning(f"Ресторан не найден: {restaurant_code}")
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        menu_data = fetch_menu_data(restaurant_id)
        conn.close()
        return jsonify(menu_data)
    except Exception as e:
        logger.error(f"Ошибка обработки запроса меню: {e}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/menu/<restaurant_code>', methods=['POST'])
def add_menu_item(restaurant_code):
    logger.info(f"Добавление позиции в меню для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = %s', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        data = request.get_json()

        cursor.execute('SELECT id FROM MenuCategories WHERE name = %s AND restaurant_id = %s',
                       (data['category'], restaurant_id))
        category = cursor.fetchone()
        if not category:
            cursor.execute('INSERT INTO MenuCategories (name, restaurant_id) VALUES (%s, %s) RETURNING id',
                           (data['category'], restaurant_id))
            category_id = cursor.fetchone()['id']
        else:
            category_id = category['id']

        cursor.execute('''
            INSERT INTO MenuItems (category_id, name, portion_price, bottle_price, weight, image, description, is_alcohol, in_stop_list)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        ''', (category_id, data['name'], data['portion_price'], data['bottle_price'],
              data['weight'], data['image'], data['description'], data['is_alcohol'], data['in_stop_list']))

        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/menu/<restaurant_code>/<int:item_id>', methods=['PUT'])
def update_menu_item(restaurant_code, item_id):
    logger.info(f"Обновление позиции {item_id} для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = %s', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        data = request.get_json()

        cursor.execute('SELECT id FROM MenuCategories WHERE name = %s AND restaurant_id = %s',
                       (data['category'], restaurant_id))
        category = cursor.fetchone()
        if not category:
            cursor.execute('INSERT INTO MenuCategories (name, restaurant_id) VALUES (%s, %s) RETURNING id',
                           (data['category'], restaurant_id))
            category_id = cursor.fetchone()['id']
        else:
            category_id = category['id']

        cursor.execute('''
            UPDATE MenuItems 
            SET category_id = %s, name = %s, portion_price = %s, bottle_price = %s, weight = %s, 
                image = %s, description = %s, is_alcohol = %s, in_stop_list = %s
            WHERE id = %s
        ''', (category_id, data['name'], data['portion_price'], data['bottle_price'],
              data['weight'], data['image'], data['description'], data['is_alcohol'],
              data['in_stop_list'], item_id))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Позиция не найдена"}), 404

        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/menu/<restaurant_code>/<int:item_id>', methods=['DELETE'])
def delete_menu_item(restaurant_code, item_id):
    logger.info(f"Удаление позиции {item_id} для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = %s', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        cursor.execute('DELETE FROM MenuItems WHERE id = %s', (item_id,))
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Позиция не найдена"}), 404

        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/orders/<restaurant_code>', methods=['GET'])
def get_orders(restaurant_code):
    logger.info(f"Получение заказов для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = %s', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            logger.warning(f"Ресторан не найден: {restaurant_code}")
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        cursor.execute('''
            SELECT id, last_name, first_name, phone, payment_method, delivery_method, room_number, total, timestamp, comment, status
            FROM Orders WHERE restaurant_id = %s
            ORDER BY timestamp DESC
        ''', (restaurant_id,))
        orders = cursor.fetchall()
        logger.debug(f"Сырые данные заказов из базы: {json.dumps(orders, ensure_ascii=False, default=str)}")

        orders_data = []
        for order in orders:
            cursor.execute('''
                SELECT item_id, name, price, quantity, is_alcohol
                FROM OrderItems WHERE order_id = %s
            ''', (order['id'],))
            items = cursor.fetchall()
            logger.debug(f"Заказ {order['id']}: status={order['status']}, comment={order['comment']}")
            orders_data.append({
                "id": order['id'] or 0,
                "customer": {
                    "last_name": order['last_name'] or '',
                    "first_name": order['first_name'] or '',
                    "phone": order['phone'] or '',
                    "room_number": order['room_number'] or ''
                },
                "order_details": {
                    "payment_method": order['payment_method'] or 'cash',
                    "delivery_method": order['delivery_method'] or 'delivery',
                    "items": [
                        {
                            "item_id": item['item_id'] or 0,
                            "name": item['name'] or 'Без названия',
                            "price": float(item['price']) if item['price'] is not None else 0.0,
                            "quantity": item['quantity'] or 0,
                            "is_alcohol": item['is_alcohol'] or False
                        } for item in items
                    ],
                    "total": float(order['total']) if order['total'] is not None else 0.0,
                    "timestamp": order['timestamp'].isoformat() if order['timestamp'] else '2025-01-01T00:00:00',
                    "comment": order['comment'] or '',
                    "status": order['status'] or 'pending'
                }
            })

        conn.close()
        logger.debug(f"Возвращено {len(orders_data)} заказов: {json.dumps(orders_data, ensure_ascii=False)}")
        return jsonify(orders_data)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/order/<restaurant_code>', methods=['POST'])
def add_order(restaurant_code):
    logger.info(f"Добавление заказа для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = %s', (restaurant_code,))
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
        comment = data.get('comment', '')
        status = 'pending'

        total = float(order_details['total'])
        cursor.execute('''
            INSERT INTO Orders (restaurant_id, last_name, first_name, phone, payment_method, delivery_method, room_number, total, timestamp, comment, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        ''', (restaurant_id, customer['lastName'], customer['firstName'], customer['phone'],
              order_details['paymentMethod'], order_details['deliveryMethod'], customer['roomNumber'],
              total, data['timestamp'], comment, status))

        order_id = cursor.fetchone()['id']
        for item in order_details['items']:
            cursor.execute('''
                INSERT INTO OrderItems (order_id, item_id, name, price, quantity, is_alcohol)
                VALUES (%s, %s, %s, %s, %s, %s)
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

@flask_app.route('/api/order/<restaurant_code>/<int:order_id>/status', methods=['PUT'])
def update_order_status(restaurant_code, order_id):
    logger.info(f"Обновление статуса заказа {order_id} для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = %s', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        data = request.get_json()
        status = data.get('status')
        logger.debug(f"Получен статус для заказа {order_id}: {status}")
        if not status or status not in ['pending', 'confirmed', 'completed', 'cancelled']:
            conn.close()
            return jsonify({"error": "Некорректный статус"}), 400

        cursor.execute('''
            UPDATE Orders 
            SET status = %s
            WHERE id = %s AND restaurant_id = %s
        ''', (status, order_id, restaurant['id']))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Заказ не найден"}), 404

        conn.commit()
        conn.close()
        logger.debug(f"Статус заказа {order_id} обновлён на {status}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/api/order/<restaurant_code>/<int:order_id>/comment', methods=['PUT'])
def update_order_comment(restaurant_code, order_id):
    logger.info(f"Обновление комментария заказа {order_id} для ресторана: {restaurant_code}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = %s', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            conn.close()
            return jsonify({"error": "Ресторан не найден"}), 404

        data = request.get_json()
        comment = data.get('comment', '')
        logger.debug(f"Получен комментарий для заказа {order_id}: {comment}")

        cursor.execute('''
            UPDATE Orders 
            SET comment = %s
            WHERE id = %s AND restaurant_id = %s
        ''', (comment, order_id, restaurant['id']))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Заказ не найден"}), 404

        conn.commit()
        conn.close()
        logger.debug(f"Комментарий заказа {order_id} обновлён: {comment}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

# Статические файлы
@flask_app.route('/static/<path:path>')
def serve_static_flask(path):
    logger.info(f"Запрос статического файла: /static/{path}")
    try:
        return send_from_directory('static', path)
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла /static/{path}: {e}")
        return jsonify({"error": f"Файл не найден: {path}"}), 404

@flask_app.route('/debug/files', methods=['GET'])
def debug_files():
    logger.info("Запрос списка статических файлов")
    try:
        files = os.listdir('static')
        logger.debug(f"Статические файлы: {files}")
        return jsonify({"static_files": files})
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов: {e}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/debug/db', methods=['GET'])
def debug_db():
    logger.info("Запрос проверки базы данных")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT unique_code FROM Restaurants')
        restaurants = [row['unique_code'] for row in cursor.fetchall()]
        conn.close()
        logger.debug(f"Рестораны в базе: {restaurants}")
        return jsonify({"restaurants": restaurants})
    except Exception as e:
        logger.error(f"Ошибка проверки базы данных: {e}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/test', methods=['GET'])
def test_route():
    logger.info("Запрос тестового маршрута")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Запуск Flask на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)
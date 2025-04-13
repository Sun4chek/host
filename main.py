import json
import os
import sqlite3
import logging
import subprocess
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

# Конфигурация
BASE_URL = os.getenv("BASE_URL", "https://buhtarest-api.onrender.com")
DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'restaurant.db')
REPO_DIR = os.path.dirname(__file__)
GIT_TOKEN = os.getenv("GIT_TOKEN")
REPO_URL = os.getenv("REPO_URL", "https://github.com/<your-username>/<your-repo>.git")  # Замените на ваш репозиторий

# Проверка GIT_TOKEN
if not GIT_TOKEN:
    logger.error("GIT_TOKEN не установлен в переменных окружения")

# Инициализация Flask
flask_app = Flask(__name__)
CORS(flask_app, resources={r"/api/*": {"origins": "*"}})

# Функция для сохранения базы данных в репозиторий
def save_db_to_repo():
    logger.info("Попытка сохранения restaurant.db в репозиторий")
    try:
        os.chdir(REPO_DIR)
        # Настраиваем Git
        subprocess.run(["git", "config", "user.email", "render@buhtarest.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Render Bot"], check=True)
        logger.debug("Git user.email и user.name настроены")

        # Проверяем изменения в db/restaurant.db
        result = subprocess.run(["git", "status", "--porcelain", "db/restaurant.db"], capture_output=True, text=True)
        if not result.stdout:
            logger.info("Нет изменений в restaurant.db для коммита")
            return

        # Добавляем файл
        subprocess.run(["git", "add", "db/restaurant.db"], check=True)
        logger.debug("Файл db/restaurant.db добавлен в git")

        # Коммитим
        subprocess.run(["git", "commit", "-m", "Update restaurant.db"], check=True)
        logger.debug("Коммит создан")

        # Push с использованием токена
        auth_url = REPO_URL.replace("https://", f"https://{GIT_TOKEN}@")
        subprocess.run(["git", "push", auth_url, "main"], check=True)
        logger.info("База данных успешно сохранена в репозиторий")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при выполнении git-команды: {e}, stderr: {e.stderr}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при сохранении базы данных: {e}")

# Подключение к базе данных
def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
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
        logger.debug(f"Меню: {menu_data}")
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
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
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
        conn.close()
        save_db_to_repo()
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
        conn.close()
        save_db_to_repo()
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
        conn.close()
        save_db_to_repo()
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
    logger.info(f"Добавление заказа для ресторана: {restaurant_code}")
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
        save_db_to_repo()
        return jsonify({"status": "success", "order_id": order_id}), 200
    except ValueError as ve:
        logger.error(f"Ошибка преобразования данных: {ve}")
        conn.close()
        return jsonify({"error": f"Ошибка данных: {ve}"}), 400
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа: {e}")
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
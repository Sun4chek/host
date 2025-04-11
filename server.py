from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import sqlite3
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db', 'restaurant.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
                "image": item['image'] or 'https://via.placeholder.com/100',
                "description": item['description'],
                "is_alcohol": bool(item['is_alcohol']),
                "in_stop_list": bool(item['in_stop_list'])
            } for item in items
        ]
    conn.close()
    return menu_data

@app.route('/api/menu/<restaurant_code>', methods=['GET'])
def get_menu(restaurant_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        menu_data = fetch_menu_data(restaurant_id)
        return jsonify(menu_data)
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/menu/<restaurant_code>', methods=['POST'])
def add_menu_item(restaurant_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
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
        print(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/menu/<restaurant_code>/<int:item_id>', methods=['PUT'])
def update_menu_item(restaurant_code, item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
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
            return jsonify({"error": "Позиция не найдена"}), 404

        conn.commit()
        menu_data = fetch_menu_data(restaurant_id)
        socketio.emit('menu_updated', menu_data)
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/menu/<restaurant_code>/<int:item_id>', methods=['DELETE'])
def delete_menu_item(restaurant_code, item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        cursor.execute('DELETE FROM MenuItems WHERE id = ?', (item_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Позиция не найдена"}), 404

        conn.commit()
        menu_data = fetch_menu_data(restaurant_id)
        socketio.emit('menu_updated', menu_data)
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<restaurant_code>', methods=['GET'])
def get_orders(restaurant_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
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
                    "items": [{"item_id": item['item_id'], "name": item['name'], "price": item['price'], "quantity": item['quantity'], "is_alcohol": bool(item['is_alcohol'])} for item in items],
                    "total": order['total'],
                    "timestamp": order['timestamp']
                }
            })

        conn.close()
        return jsonify(orders_data)
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/order/<restaurant_code>', methods=['POST'])
def add_order(restaurant_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', (restaurant_code,))
        restaurant = cursor.fetchone()
        if not restaurant:
            print(f"Ресторан с кодом {restaurant_code} не найден")
            return jsonify({"error": "Ресторан не найден"}), 404

        restaurant_id = restaurant['id']
        data = request.get_json()
        print(f"Получен заказ: {data}")

        if not data.get('customer') or not data.get('orderDetails'):
            print("Ошибка: отсутствуют customer или orderDetails")
            return jsonify({"error": "Некорректные данные заказа"}), 400

        customer = data['customer']
        order_details = data['orderDetails']

        print(f"Customer: {customer}")
        print(f"Order Details: {order_details}")

        total = float(order_details['total'])  # Преобразуем total в float
        print(f"Total преобразован в float: {total}")

        cursor.execute('''
            INSERT INTO Orders (restaurant_id, last_name, first_name, phone, payment_method, delivery_method, room_number, total, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (restaurant_id, customer['lastName'], customer['firstName'], customer['phone'],
              order_details['paymentMethod'], order_details['deliveryMethod'], customer['roomNumber'],
              total, data['timestamp']))

        order_id = cursor.lastrowid
        print(f"Создан заказ с ID: {order_id}")

        for item in order_details['items']:
            print(f"Добавление позиции: {item}")
            cursor.execute('''
                INSERT INTO OrderItems (order_id, item_id, name, price, quantity, is_alcohol)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, item.get('item_id'), item['name'], float(item['price']), item['quantity'], item.get('isAlcohol', False)))  # Используем isAlcohol

        conn.commit()
        conn.close()
        print(f"Заказ успешно сохранён с ID: {order_id}")
        return jsonify({"status": "success", "order_id": order_id}), 200
    except ValueError as ve:
        print(f"Ошибка преобразования данных: {ve}")
        return jsonify({"error": f"Ошибка данных: {ve}"}), 400
    except Exception as e:
        print(f"Ошибка при сохранении заказа: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
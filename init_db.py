import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'db')
DB_PATH = os.path.join(DB_DIR, 'restaurant.db')

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Таблица Restaurants
cursor.execute('''
CREATE TABLE IF NOT EXISTS Restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unique_code TEXT NOT NULL UNIQUE
)''')

# Таблица MenuCategories
cursor.execute('''
CREATE TABLE IF NOT EXISTS MenuCategories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER,
    name TEXT NOT NULL,
    FOREIGN KEY (restaurant_id) REFERENCES Restaurants(id)
)''')

# Таблица MenuItems
cursor.execute('''
CREATE TABLE IF NOT EXISTS MenuItems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    name TEXT NOT NULL,
    portion_price REAL,
    bottle_price REAL,
    weight TEXT,
    image TEXT,
    description TEXT,
    is_alcohol INTEGER DEFAULT 0,
    in_stop_list INTEGER DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES MenuCategories(id)
)''')

# Новая таблица Orders
cursor.execute('''
CREATE TABLE IF NOT EXISTS Orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    delivery_method TEXT NOT NULL,
    room_number TEXT,
    total REAL NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (restaurant_id) REFERENCES Restaurants(id)
)''')

# Новая таблица OrderItems
cursor.execute('''
CREATE TABLE IF NOT EXISTS OrderItems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    item_id INTEGER,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    is_alcohol INTEGER DEFAULT 0,
    FOREIGN KEY (order_id) REFERENCES Orders(id),
    FOREIGN KEY (item_id) REFERENCES MenuItems(id)
)''')

# Инициализация данных
cursor.execute('INSERT OR IGNORE INTO Restaurants (name, unique_code) VALUES (?, ?)', ('Бухта', 'BUHTA123'))
restaurant_id = cursor.execute('SELECT id FROM Restaurants WHERE unique_code = ?', ('BUHTA123',)).fetchone()[0]

categories = [
    ('Основные блюда', restaurant_id),
    ('Напитки', restaurant_id),
    ('Первые блюда', restaurant_id),
    ('Салаты', restaurant_id),
    ('Морепродукты', restaurant_id),
    ('Пасты', restaurant_id),
    ('Мангал', restaurant_id),
    ('Алкоголь', restaurant_id),
    ('Крепкий алкоголь', restaurant_id),
    ('Вино', restaurant_id),
    ('Пиво', restaurant_id)
]
cursor.executemany('INSERT OR IGNORE INTO MenuCategories (name, restaurant_id) VALUES (?, ?)', categories)

category_ids = {}
for category_name in [c[0] for c in categories]:
    cursor.execute('SELECT id FROM MenuCategories WHERE name = ? AND restaurant_id = ?', (category_name, restaurant_id))
    category_ids[category_name] = cursor.fetchone()[0]

menu_items = [
    # Основные блюда
    (category_ids['Основные блюда'], 'Сковорода куриная', 450, None, '360г',
     'https://i.obozrevatel.com/food/recipemain/2018/11/23/7762801.jpg?size=1944x924',
     'Курица с овощами в сливочном соусе', 0, 0),
    (category_ids['Основные блюда'], 'Куриная отбивная', 400, None, '200г',
     'https://ferma-m2.ru/images/shop/recipe_image/crop_rimskiy.jpg', 'Нежная куриная грудка в панировке', 0, 0),
    (category_ids['Основные блюда'], 'Сковорода свиная', 530, None, '360г',
     'https://whogrill.ru/upload/resize_cache/webp/iblock/0aa/0aadb32c17da2cc609aaad04829c47fb.webp',
     'Свинина с овощами и грибами', 0, 0),

    # Первые блюда
    (category_ids['Первые блюда'], 'Борщ', 400, None, '350г',
     'https://i.obozrevatel.com/food/recipemain/2018/11/23/7762801.jpg?size=1944x924', 'Традиционный украинский борщ',
     0, 0),
    (category_ids['Первые блюда'], 'Солянка', 450, None, '350г',
     'https://ferma-m2.ru/images/shop/recipe_image/crop_rimskiy.jpg', 'Густой суп с мясом и солеными огурцами', 0, 0),
    (category_ids['Первые блюда'], 'Суп лапша', 300, None, '300г',
     'https://whogrill.ru/upload/resize_cache/webp/iblock/0aa/0aadb32c17da2cc609aaad04829c47fb.webp',
     'Куриный суп с домашней лапшой', 0, 0),

    # Салаты
    (category_ids['Салаты'], 'Цезарь с курицей', 350, None, '250г',
     'https://i.obozrevatel.com/food/recipemain/2018/11/23/7762801.jpg?size=1944x924',
     'Классический салат с курицей, крутонами и соусом', 0, 0),
    (category_ids['Салаты'], 'Греческий салат', 400, None, '300г',
     'https://ferma-m2.ru/images/shop/recipe_image/crop_rimskiy.jpg', 'Свежие овощи с фетой и оливками', 0, 0),
    (category_ids['Салаты'], 'Салат с креветками', 450, None, '300г',
     'https://whogrill.ru/upload/resize_cache/webp/iblock/0aa/0aadb32c17da2cc609aaad04829c47fb.webp',
     'Креветки с авокадо и листьями салата', 0, 0),

    # Напитки
    (category_ids['Напитки'], 'Borjomi (стекло)', 250, None, '0,5 л', 'https://example.com/borjomi.jpg',
     'Минеральная вода в стеклянной бутылке', 0, 0),
    (category_ids['Напитки'], 'Вода "Крымская" (стекло) газ./сл.газ.', 120, None, '0,5 л',
     'https://example.com/krymskaya-water.jpg', 'Минеральная вода в стекле, газированная или слегка газированная', 0,
     0),
    (category_ids['Напитки'], '"Кола" (стекло)', 250, None, '0,33 л', 'https://example.com/cola.jpg',
     'Классическая кола в стеклянной бутылке', 0, 0),
    (
    category_ids['Напитки'], 'Яблоко', 100, 400, '200мл / 1л', 'images/apple-juice.jpg', 'Свежевыжатый яблочный сок', 0,
    0),
    (category_ids['Напитки'], 'Апельсин', 100, 400, '200мл / 1л', 'images/orange-juice.jpg',
     'Свежевыжатый апельсиновый сок', 0, 0),
    (
    category_ids['Напитки'], 'Вишня', 100, 400, '200мл / 1л', 'images/cherry-juice.jpg', 'Свежевыжатый вишневый сок', 0,
    0),
    (category_ids['Напитки'], 'Мультифрукт', 100, 400, '200мл / 1л', 'images/multifruit-juice.jpg',
     'Свежевыжатый мультифруктовый сок', 0, 0),
    (
    category_ids['Напитки'], 'Томат', 100, 400, '200мл / 1л', 'images/tomato-juice.jpg', 'Свежевыжатый томатный сок', 0,
    0),
    (category_ids['Напитки'], 'Клюквенный морс', 100, 400, '200мл / 1л', 'images/cranberry-morse.jpg',
     'Освежающий клюквенный морс', 0, 0),
    (category_ids['Напитки'], 'Чёрная смородина', 100, 400, '200мл / 1л', 'images/blackcurrant-morse.jpg',
     'Ароматный морс из черной смородины', 0, 0),
    (category_ids['Напитки'], 'Имбирный', 700, None, '1л', 'images/ginger-lemonade.jpg',
     'Лимонад с пряным вкусом имбиря', 0, 0),
    (category_ids['Напитки'], 'Цитрусовый микс', 650, None, '1л', 'images/citrus-lemonade.jpg',
     'Освежающий лимонад с цитрусовыми нотами', 0, 0),
    (category_ids['Напитки'], 'Лавандовый', 600, None, '1л', 'images/lavender-lemonade.jpg',
     'Лимонад с нежным ароматом лаванды', 0, 0),
    (category_ids['Напитки'], 'Огурец-базилик', 800, None, '1л', 'images/cucumber-lemonade.jpg',
     'Необычный лимонад с огурцом и базиликом', 0, 0),
    (category_ids['Напитки'], 'Клубника-базилик', 700, None, '1л', 'images/strawberry-lemonade.jpg',
     'Лимонад с сочетанием клубники и базилика', 0, 0),
    (category_ids['Напитки'], 'Чай облепиховый', 300, 400, '500 мл / 700 мл',
     'https://example.com/sea-buckthorn-tea.jpg', 'Чай с ярким вкусом облепихи', 0, 0),
    (category_ids['Напитки'], 'Чай имбирный', 300, 400, '500 мл / 700 мл', 'https://example.com/ginger-tea.jpg',
     'Пряный чай с имбирём', 0, 0),
    (category_ids['Напитки'], 'Чай "Крымский сбор"', 300, 400, '500 мл / 700 мл', 'https://example.com/krymsky-tea.jpg',
     'Чай из крымских трав', 0, 0),
    (category_ids['Напитки'], 'Чай черный', 250, 350, '500 мл / 700 мл', 'https://example.com/black-tea.jpg',
     'Классический черный чай', 0, 0),
    (category_ids['Напитки'], 'Чай зеленый', 250, 350, '500 мл / 700 мл', 'https://example.com/green-tea.jpg',
     'Классический зеленый чай', 0, 0),
    (category_ids['Напитки'], 'Молочный улун', 250, 350, '500 мл / 700 мл', 'https://example.com/milk-oolong.jpg',
     'Чай с мягким сливочным вкусом', 0, 0),
    (category_ids['Напитки'], 'Эспрессо', 150, None, '30 мл', 'https://example.com/espresso.jpg',
     'Классический эспрессо', 0, 0),
    (category_ids['Напитки'], 'Американо', 150, None, '120 мл', 'https://example.com/americano.jpg',
     'Эспрессо с добавлением горячей воды', 0, 0),
    (category_ids['Напитки'], 'Американо с молоком', 200, None, '150 мл', 'https://example.com/americano-milk.jpg',
     'Американо с добавлением молока', 0, 0),
    (category_ids['Напитки'], 'Капучино', 200, None, '150 мл', 'https://example.com/cappuccino.jpg',
     'Эспрессо с молочной пеной', 0, 0),
    (category_ids['Напитки'], 'Латте', 250, None, '200 мл', 'https://example.com/latte.jpg',
     'Эспрессо с большим количеством молока', 0, 0),

    # Крепкий алкоголь
    (category_ids['Крепкий алкоголь'], 'Виски Jameson', None, 7000, '0,7 л', 'images/jameson.png',
     'Ирландский виски с мягким вкусом', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Monkey Shoulder', None, 9800, '0,7 л', 'images/monkey.png',
     'Шотландский купажированный виски', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Red Label', None, 3920, '0,7 л', 'images/red-label.png', 'Шотландский виски', 1,
     0),
    (category_ids['Крепкий алкоголь'], 'Виски Ballantines', None, 6000, '0,7 л', 'images/ballentines.png',
     'Шотландский виски с насыщенным вкусом', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Tullamore Dew', None, 9800, '0,7 л', 'images/tullamore.png', 'Ирландский виски',
     1, 0),
    (category_ids['Крепкий алкоголь'], 'Виски Chivas Regal', None, 12500, '0,7 л', 'images/chivas-regal.png',
     'Элитный шотландский виски', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Коктель резерв 5 лет', None, 2200, '0,7 л', 'images/koktebel-5.jpg',
     'Бренди с выдержкой 5 лет', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Коктель резерв 7 лет', None, 3200, '0,7 л', 'images/koktebel-7.png',
     'Бренди с выдержкой 7 лет', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Македонский 3 года', None, 2000, '0,7 л', 'images/makedon-3.png',
     'Бренди с выдержкой 3 года', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Лезгинка 6 лет', None, 2200, '0,7 л', 'images/lezginka-6.png',
     'Бренди с выдержкой 6 лет', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Старейшина Ecological', None, 2200, '0,7 л', 'images/ecological-star7.png',
     'Экологически чистый бренди', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Арарат 3 года', None, 4060, '0,7 л', 'images/ararat-3.png',
     'Армянский коньяк 3 года выдержки', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Арарат 5 лет', None, 4830, '0,7 л', 'images/ararat-5.png',
     'Армянский коньяк 5 лет выдержки', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Арарат 10 лет', None, 6500, '0,5 л', 'images/ararat-10.png',
     'Армянский коньяк 10 лет выдержки', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Jägermeister', None, 5600, '0,7 л', 'images/jager.png', 'Травяной ликер', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Havana Club', None, 5800, '0,7 л', 'images/Havana-club.png', 'Кубинский ром', 1,
     0),
    (category_ids['Крепкий алкоголь'], 'Captain Morgan', None, 3500, '0,7 л', 'images/CAptein-morgan.png',
     'Карибский ром', 1, 0),
    (
    category_ids['Крепкий алкоголь'], 'Beefeater', None, 6400, '0,7 л', 'images/defeater.png', 'Лондонский джин', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Olmeca Blanco', None, 7000, '0,7 л', 'images/olmeca-blanco.png',
     'Мексиканская текила', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Organic vodka Чистые Росы пшеничная', None, 5600, '0,7 л',
     'images/chist-rosa.png', 'Органическая водка', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Царская золотая', None, 2100, '0,7 л', 'images/tzar-gold.png',
     'Водка премиум-класса', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Ханская', None, 1200, '0,5 л', 'images/hanska.png', 'Традиционная водка', 1, 0),
    (category_ids['Крепкий алкоголь'], 'Коктебель Grappe', None, 2000, '0,5 л', 'images/grappe.png',
     'Классическая водка', 1, 0),

    # Вино
    (category_ids['Вино'], 'Просекко Чинзано', None, 4200, '0,75 л', 'images/prosecco-chinzano.png',
     'Итальянское игристое вино', 1, 0),
    (category_ids['Вино'], 'PROSECCO Don Treviso', None, 2600, '0,75 л', 'images/prosecco.png',
     'Итальянское игристое вино', 1, 0),
    (category_ids['Вино'], 'Новый свет коллекционное брют белое', None, 2200, '0,75 л',
     'images/new-light-brut-white.png', 'Крымское игристое вино', 1, 0),
    (category_ids['Вино'], 'Новый свет белое полусладкое', None, 2000, '0,75 л', 'images/new-light-white.png',
     'Крымское игристое вино', 1, 0),
    (category_ids['Вино'], 'Золотая балка брют белое', None, 1450, '0,75 л', 'images/gold-balka-white.png',
     'Крымское игристое вино', 1, 0),
    (category_ids['Вино'], 'Золотая балка Frizzante розовое', None, 1450, '0,75 л', 'images/gold-balka-pink.png',
     'Крымское игристое вино', 1, 0),
    (category_ids['Вино'], 'Золотая балка Moscato белое', None, 1450, '0,75 л', 'images/gold-balka-white-muskat.png',
     'Крымское игристое вино', 1, 0),
    (category_ids['Вино'], 'PAFOS DIVINE', None, 1200, '0,75 л', 'images/pafos.png', 'Итальянское игристое вино', 1, 0),
    (category_ids['Вино'], 'Совиньон Блан ESSE', None, 1600, '0,75 л', 'images/esse-sivinion-blan.png',
     'Белое сухое вино', 1, 0),
    (category_ids['Вино'], 'Каберне отборное ESSE', None, 1600, '0,75 л', 'images/esse-kaberne-otbornoe.png',
     'Красное сухое вино', 1, 0),
    (category_ids['Вино'], 'Гевиюрцтраминер ESSE', None, 2600, '0,75 л', 'images/esse-gur.png', 'Белое ароматное вино',
     1, 0),
    (category_ids['Вино'], 'Каберне Фран ESSE', None, 2300, '0,75 л', 'images/esse-kaberne-fran.png',
     'Красное сухое вино', 1, 0),
    (category_ids['Вино'], 'Совиньон ALMA VALLEY', None, 1600, '0,75 л', 'images/alma-sovinien-white.png',
     'Белое сухое вино', 1, 0),
    (
    category_ids['Вино'], 'Пикник ALMA VALLEY', None, 1500, '0,75 л', 'images/alma-picnick.png', 'Белое полусухое вино',
    1, 0),
    (category_ids['Вино'], 'Весеннее ALMA VALLEY', None, 1600, '0,75 л', 'images/alma-spring.png',
     'Белое полусладкое вино', 1, 0),
    (category_ids['Вино'], 'Каберне Совиньон ALMA VALLEY', None, 1800, '0,75 л', 'images/alma-caberne-red.png',
     'Красное сухое вино', 1, 0),
    (category_ids['Вино'], 'Зимнее ALMA VALLEY', None, 1600, '0,75 л', 'images/alma-winter.png',
     'Красное полусладкое вино', 1, 0),
    (
    category_ids['Вино'], 'Траминер INKERMAN', None, 1500, '0,75 л', 'images/inkerman-traminer.png', 'Белое сухое вино',
    1, 0),
    (category_ids['Вино'], 'Каберне совиньон розовое INKERMAN', None, 1650, '0,75 л', 'images/sevre-pink.png',
     'Розовое сухое вино', 1, 0),
    (category_ids['Вино'], 'Рислинг INKERMAN', None, 1500, '0,75 л', 'images/inkerman-risling.png',
     'Белое полусухое вино', 1, 0),
    (category_ids['Вино'], 'Мускат INKERMAN', None, 1500, '0,75 л', 'images/inkerman-muskat-white.png',
     'Белое полусладкое вино', 1, 0),
    (category_ids['Вино'], 'Каберне резерв INKERMAN', None, 1800, '0,75 л', 'images/inkerman-kaberne-reserve-red.png',
     'Красное сухое вино', 1, 0),
    (category_ids['Вино'], 'Пино Нуар INKERMAN', None, 1800, '0,75 л', 'images/inkerman-pino-nuar.png',
     'Красное полусладкое вино', 1, 0),
    (category_ids['Вино'], 'Херес Массандра', None, 1800, '0,75 л', 'images/massandra-heres.png', 'Крепкое вино', 1, 0),
    (
    category_ids['Вино'], 'Мадера Крымская', None, 2100, '0,75 л', 'images/massandra-modera.png', 'Крепкое вино', 1, 0),
    (category_ids['Вино'], 'Портвейн красный Ливадия', None, 1700, '0,75 л', 'images/massandra-portvein-red-livadi.png',
     'Красный портвейн', 1, 0),
    (category_ids['Вино'], 'Портвейн белый Крымский', None, 1500, '0,75 л', 'images/massandra-portvein-white.png',
     'Белый портвейн', 1, 0),
    (category_ids['Вино'], 'Седьмое небо князя Голицына', None, 1600, '0,75 л', 'images/massandra-seven-sky.png',
     'Белое вино', 1, 0),
    (category_ids['Вино'], 'Бастардо', None, 1900, '0,75 л', 'images/massandra-bastardo.png', 'Красное десертное вино',
     1, 0),
    (category_ids['Вино'], 'Мускат белый Красного Камня', None, 2200, '0,75 л',
     'images/massandra-muskat-white-red-stone.png', 'Белое десертное вино', 1, 0),
    (category_ids['Вино'], 'MARTINI Bianco Вермут', None, 2500, '0,75 л', 'images/martini.png', 'Белый вермут', 1, 0),

    # Пиво
    (category_ids['Пиво'], 'Крымская Ривьера светлое', None, 180, '0,450 л', 'images/crimean-riveara-light.png',
     'Светлое пиво', 1, 0),
    (category_ids['Пиво'], 'Белая скала светлое н/ф', None, 180, '0,450 л', 'images/white-scale.png',
     'Нефильтрованное светлое пиво', 1, 0),
    (category_ids['Пиво'], 'Черное гора темное', None, 180, '0,450 л', 'images/black-scale.png', 'Темное пиво', 1, 0),
    (category_ids['Пиво'], 'Stella Artois безалкогольное', None, 200, '0,440 л', 'images/stella.png',
     'Безалкогольное пиво', 0, 0),
]
cursor.executemany('INSERT OR IGNORE INTO MenuItems (category_id, name, portion_price, bottle_price, weight, image, description, is_alcohol, in_stop_list) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', menu_items)

conn.commit()
print(f"База данных создана и заполнена: {DB_PATH}")
conn.close()
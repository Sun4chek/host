import subprocess
import requests
import re
import os
import time

def get_ngrok_url():
    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        data = response.json()
        public_url = data['tunnels'][0]['public_url']
        return public_url
    except Exception as e:
        print(f"Ошибка получения URL ngrok: {e}")
        return None

def update_file(file_path, new_url):
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл не найден - {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_url_pattern = r'https?://[a-z0-9-]+\.ngrok-free\.app(?:/[^\'" ]*)?'
    new_urls = {
        r'/api/menu/BUHTA123': f"{new_url}/api/menu/BUHTA123",
        r'/api/order/BUHTA123': f"{new_url}/api/order/BUHTA123",
        r'/api/orders/BUHTA123': f"{new_url}/api/orders/BUHTA123",
        r'/api/menu/BUHTA123/\d+': f"{new_url}/api/menu/BUHTA123/",  # Для PUT/DELETE с ID
        r'/static/user_webapp.html': f"{new_url}/static/user_webapp.html",
        r'/static/admin_webapp.html': f"{new_url}/static/admin_webapp.html",
    }

    updated_content = content
    changes_made = False

    for pattern, replacement in new_urls.items():
        full_pattern = r'https?://[a-z0-9-]+\.ngrok-free\.app' + pattern
        if re.search(full_pattern, updated_content):
            updated_content = re.sub(full_pattern, replacement, updated_content)
            changes_made = True
            print(f"Обновлён URL в {file_path}: {replacement}")

    if not changes_made:
        base_pattern = r'https?://[a-z0-9-]+\.ngrok-free\.app'
        if re.search(base_pattern, updated_content):
            updated_content = re.sub(base_pattern, new_url, updated_content)
            changes_made = True
            print(f"Обновлён базовый URL в {file_path}: {new_url}")

    if not changes_made:
        print(f"Внимание: URL не обновлён в {file_path} - старый URL не найден")
        return False

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    print(f"Успешно обновлён файл: {file_path}")
    return True

def main():
    subprocess.Popen(['ngrok', 'http', '5001'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("ngrok запущен на порту 5001")
    time.sleep(2)

    new_url = get_ngrok_url()
    if not new_url:
        print("Не удалось получить URL ngrok")
        return

    files_to_update = [
        'static/user_webapp.html',
        'static/admin_webapp.html',
        'user_bot.py',
        'admin_bot.py'
    ]

    for file in files_to_update:
        update_file(file, new_url)

    print(f"Новый ngrok URL: {new_url}")

if __name__ == "__main__":
    main()
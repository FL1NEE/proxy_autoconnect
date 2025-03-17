# -*- coding: utf-8 -*-
import os
import subprocess
import requests
import json
from requests.exceptions import ProxyError, ConnectTimeout

# Путь к файлу для хранения данных прокси
PROXY_DATA_FILE: str = "proxy_data.json"

# Класс для хранения данных прокси
class ProxyData:
    def __init__(self):
        self.proxy_server: str = ""
        self.username: str = ""
        self.password: str = ""

proxy_data = ProxyData()

def get_current_ip(proxy_url: str = None) -> str:
    """Получение текущего IP-адреса"""
    try:
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        response = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=30)
        return response.json().get("ip")
    except ProxyError as e:
        if "407 Proxy Authentication Required" in str(e):
            print("Ошибка: Прокси требует аутентификацию. Проверьте логин и пароль.")
        else:
            print(f"Ошибка при подключении через прокси: {e}")
        return None
    except ConnectTimeout:
        print("Ошибка: Время ожидания подключения истекло. Проверьте настройки прокси.")
        return None
    except Exception as e:
        print(f"Ошибка при получении IP-адреса: {e}")
        return None

def save_proxy_data() -> None:
    """Сохранение данных прокси в файл"""
    proxy_data_dict = {
        "proxy_server": proxy_data.proxy_server,
        "username": proxy_data.username,
        "password": proxy_data.password,
    }
    with open(PROXY_DATA_FILE, "w") as f:
        json.dump(proxy_data_dict, f)

def load_proxy_data() -> bool:
    """Загрузка данных прокси из файла"""
    if os.path.exists(PROXY_DATA_FILE):
        with open(PROXY_DATA_FILE, "r") as f:
            proxy_data_dict = json.load(f)
            proxy_data.proxy_server = proxy_data_dict.get("proxy_server", "")
            proxy_data.username = proxy_data_dict.get("username", "")
            proxy_data.password = proxy_data_dict.get("password", "")
        return True
    return False

def parse_proxy_input(proxy_input: str) -> tuple:
    """Разбор строки прокси в формате login:pass@ip:port"""
    try:
        credentials, server = proxy_input.split("@")
        username, password = credentials.split(":")
        ip, port = server.split(":")
        return ip, port, username, password
    except ValueError:
        print("Неверный формат прокси. Используйте формат: login:pass@ip:port")
        return None, None, None, None

def is_proxy_configured() -> bool:
    """Проверка, были ли данные прокси уже добавлены в /etc/environment"""
    if os.path.exists("/etc/environment"):
        with open("/etc/environment", "r") as f:
            content = f.read()
            return "http_proxy" in content and "https_proxy" in content
    return False

def setup_proxy(proxy_input: str) -> bool:
    """Настройка прокси"""
    ip, port, username, password = parse_proxy_input(proxy_input)
    if not ip or not port or not username or not password:
        print("Ошибка при разборе данных прокси.")
        return False

    proxy_data.proxy_server = f"{ip}:{port}"
    proxy_data.username = username
    proxy_data.password = password
    save_proxy_data()

    # Установка глобального прокси
    with open("/etc/environment", "a") as f:
        f.write(f"\nhttp_proxy=http://{username}:{password}@{ip}:{port}\n")
        f.write(f"https_proxy=http://{username}:{password}@{ip}:{port}\n")
        f.write("no_proxy=\"localhost,127.0.0.1,::1\"\n")
    print("Прокси успешно настроен.")
    return True

def check_proxy_availability(proxy_url: str) -> bool:
    """Проверка доступности прокси"""
    try:
        response = requests.get("https://ipv4.jsonip.com/", proxies={"http": proxy_url, "https": proxy_url}, timeout=30)
        if response.status_code == 200:
            print(f"Прокси работает. Полученный IP: {response.json()['ip']}")
            return True
        else:
            print("Прокси не работает. Статус код:", response.status_code)
            return False
    except ProxyError as e:
        if "407 Proxy Authentication Required" in str(e):
            print("Ошибка: Прокси требует аутентификацию. Проверьте логин и пароль.")
        else:
            print(f"Ошибка при проверке прокси: {e}")
        return False
    except ConnectTimeout:
        print("Ошибка: Время ожидания подключения истекло. Проверьте настройки прокси.")
        return False
    except Exception as e:
        print(f"Ошибка при проверке прокси: {e}")
        return False

def reboot_system() -> None:
    """Перезагрузка системы"""
    print("Для применения настроек прокси требуется перезагрузка системы.")
    confirm = input("Хотите перезагрузить систему сейчас? (y/n): ")
    if confirm == "y":
        print("Перезагрузка системы...")
        os.system("sudo reboot")
    else:
        print("Перезагрузите систему вручную для применения изменений.")

def main() -> None:
    while True:
        # Шаг 1: Проверка текущего IP-адреса
        print("Проверка текущего IP-адреса...")
        original_ip = get_current_ip()
        if not original_ip:
            print("Не удалось получить текущий IP-адрес. Проверьте подключение к интернету.")
            proxy_input = 12331
            if not setup_proxy(proxy_input):
                print("Не удалось настроить новый прокси. Повторите попытку.")
                continue
            reboot_system()
            return

        print(f"Текущий IP-адрес: {original_ip}")

        # Шаг 2: Проверка наличия настроек прокси
        if is_proxy_configured():
            print("Прокси уже настроен.")
            if not load_proxy_data():
                print("Не удалось загрузить данные прокси. Настройте прокси заново.")
                proxy_input = input("Введите данные нового прокси в формате login:pass@ip:port: ")
                if not setup_proxy(proxy_input):
                    print("Не удалось настроить новый прокси. Повторите попытку.")
                    continue
                reboot_system()
                return

            proxy_url = f"http://{proxy_data.username}:{proxy_data.password}@{proxy_data.proxy_server}"
            if not check_proxy_availability(proxy_url):
                print("Текущий прокси не работает. Настройте новый прокси.")
                proxy_input = input("Введите данные нового прокси в формате login:pass@ip:port: ")
                if not setup_proxy(proxy_input):
                    print("Не удалось настроить новый прокси. Повторите попытку.")
                    continue
                reboot_system()
                return
            else:
                print("Прокси работает корректно.")
                break
        else:
            print("Настройка прокси...")
            proxy_input = input("Введите данные прокси в формате login:pass@ip:port: ")
            if not setup_proxy(proxy_input):
                print("Не удалось настроить прокси. Повторите попытку.")
                continue
            reboot_system()
            return

if __name__ == "__main__":
    main()

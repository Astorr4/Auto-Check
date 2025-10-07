import os
import socket
import logging
import subprocess
import time
import psutil
from selenium import webdriver
from services.func_and_pass import resource_path


logger_ui = logging.getLogger(__name__)
CREATE_NO_WINDOW = 0x08000000  # Флаг для скрытия окна

# Полные пути к файлам
chrome_path = resource_path("assets/chrome-win64/chrome.exe")
chromedriver_path = resource_path("assets/chromedriver-win64/chromedriver.exe")

# Пути для сборки EXE
# chrome_path = resource_path("chrome-win64/chrome.exe")
# chromedriver_path = resource_path("chromedriver-win64/chromedriver.exe")

# Глобальные переменные для хранения процессов
_driver = None
_chromedriver_process = None
_chrome_processes = []  # Список для хранения PID процессов Chrome


def get_chromedriver():
    """Функция для запуска chromedriver и Chrome"""
    global _driver, _chromedriver_process
    if _driver is None:
        # Поиск свободного порта для ChromeDriver
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            chromedriver_port = s.getsockname()[1]
        # Запускаем ChromeDriver и сохраняем процесс
        chromedriver_proc = subprocess.Popen(
            [chromedriver_path, f"--port={chromedriver_port}"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        _chromedriver_process = chromedriver_proc
        logger_ui.info(
            f"ChromeDriver запущен на порту {chromedriver_port}, PID: {chromedriver_proc.pid}")
        # Проверяем подключение с таймаутом
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                with socket.create_connection(('localhost', chromedriver_port), timeout=1):
                    logger_ui.info(
                        f"ChromeDriver подключен на порту {chromedriver_port}")
                    break
            except (socket.timeout, ConnectionRefusedError):
                if attempt == max_attempts - 1:
                    logger_ui.error(
                        f"ChromeDriver не запущен после {max_attempts} попыток")
                    return None
                time.sleep(0.5)
        # Настройка опций Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--log-level=3')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-insecure-localhost')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-setuid-sandbox')
        options.binary_location = chrome_path
        # Создаем драйвер
        try:
            _driver = webdriver.Remote(
                command_executor=f"http://127.0.0.1:{chromedriver_port}",
                options=options
            )
            # Устанавливаем таймауты для веб-драйвера
            _driver.set_page_load_timeout(30)
            _driver.implicitly_wait(5)
            logger_ui.info('WebDriver успешно подключен')
            return _driver
        except Exception as e:
            logger_ui.error(f"Ошибка подключения к WebDriver: {e}")
            close_driver()
            return None
    return _driver


def close_driver():
    """Функция для закрытия WebDriver и Chromedriver процесса"""
    global _driver, _chromedriver_process
    # Закрываем драйвер
    if _driver is not None:
        try:
            _driver.quit()
            logger_ui.info('WebDriver закрыт')
        except Exception as e:
            logger_ui.error(f'Ошибка при закрытии WebDriver: {e}')
        finally:
            _driver = None
    # Закрываем процесс ChromeDriver
    if _chromedriver_process is not None:
        try:
            # Сначала пробуем корректно завершить
            _chromedriver_process.terminate()
            # Ждем завершения с коротким таймаутом
            chromedriver_process.wait(timeout=1)
            loggerui.info('ChromeDriver процесс завершен')
        except (subprocess.TimeoutExpired, psutil.NoSuchProcess):
            # Принудительно завершаем, если не ответил
            try:
                _chromedriver_process.kill()
                logger_ui.info('ChromeDriver процесс принудительно завершен')
            except:
                pass
        except Exception as e:
            logger_ui.error(f'Ошибка при завершении ChromeDriver: {e}')
        finally:
            _chromedriver_process = None
    # Дополнительно убиваем любые оставшиеся процессы chromedriver из папки проекта
    kill_remaining_chromedrivers()


def kill_remaining_chromedrivers():
    """Завершает любые оставшиеся процессы Chromedriver из папки проекта"""
    project_path = os.path.abspath(os.getcwd()).lower()
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            process_name = (proc.info['name'] or "").lower()
            if process_name != 'chromedriver.exe':
                continue
            exe_path = (proc.info['exe'] or "").lower()
            # Проверяем, связан ли процесс с проектом
            if project_path in exe_path:
                try:
                    proc.kill()
                    logger_ui.info(
                        f"Завершен оставшийся Chromedriver: PID {proc.info['pid']}")
                except:
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

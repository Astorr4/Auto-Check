import logging
import os
import sys
from logging.handlers import RotatingFileHandler


logger = None


def init_logging(log_callback):
    """Инициализация системы логирования"""
    global logger
    logger = log_callback


def log(message: str, message_type: str = "info"):
    """Унифицированная функция логирования в интерфейс"""
    if logger:
        logger(message, message_type)


def setup_logging():
    """Настройка логирования"""
    if getattr(sys, 'frozen', False):
        # Если программа собрана (exe)
        base_dir = os.path.dirname(sys.executable)
    else:
        # Берём путь к корню проекта (один уровень выше папки services)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(base_dir, 'Logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, 'app.log')
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    formatter = logging.Formatter(
        "%(levelname)s - %(asctime)s - %(name)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

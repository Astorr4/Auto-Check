import json
import logging
import os
import random
import sys
import threading
import time
from datetime import datetime, time as dt_time
import keyring
import psutil
import systems.a.a as a
import systems.g.g as g
import systems.k.k as k
import systems.m.m as m
import systems.mi.mi as mi
import systems.p.p as p
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QBrush, QFontMetrics, QPalette, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QSizePolicy, QFrame, QListWidget,
    QListWidgetItem, QMenu, QAction, QDialog, QLineEdit, QDialogButtonBox
)
from services.func_and_pass import login, resource_path
from services.webdriver import close_driver
logger_ui = logging.getLogger(__name__)
# Читаем конфиг
with open(resource_path('config/ui_config.json'), 'r', encoding='utf-8-sig') as f:
    config = json.load(f)
# Извлекаем нужные словари
COLORS = config.get("colors", {})
SYSTEMS_CONFIG = config.get("systems_config", {})
STATUS_ICONS = config.get("status_icons", {})
styles = config.get("styles", {})
# Глобальная блокировка для работы с системами
systems_lock = threading.Lock()
# Функция для применения стилей с подстановкой цветов


def apply_style(widget, style_key, colors):
    if style_key in styles:
        style = styles[style_key]
        # Заменяем плейсхолдеры на реальные цвета
        for color_key, color_value in colors.items():
            placeholder = "{" + color_key + "}"
            style = style.replace(placeholder, color_value)
        widget.setStyleSheet(style)


def resource_path(relative_path):
    """Получает абсолютный путь к ресурсу"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def set_environment_variable(name, value):
    """Устанавливает переменную среды"""
    import ctypes
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            'Environment',
            0,
            winreg.KEY_WRITE
        )
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x1A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_long()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            'Environment', SMTO_ABORTIFHUNG, 1000,
            ctypes.byref(result)
        )
        return True
    except Exception as e:
        logger_ui.error(f"Ошибка при установке переменной среды: {e}")
        return False


def kill_auto_check_chrome_processes():
    """Завершает процессы Chrome, связанные с авто-проверками"""
    logger_ui.info('Поиск незавершенных процессов Chrome и Chromedriver')
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            process_name = (proc.info['name'] or "").lower()
            if process_name not in ('chrome.exe', 'chromedriver.exe'):
                continue
            exe_path = proc.info['exe']
            if not exe_path:
                continue
            normalized_path = exe_path.lower()
            if ('autocheck' in normalized_path or 'auto_check' in normalized_path or
                    'appdata' in normalized_path or 'assets' in normalized_path):
                logger_ui.info(
                    f"Завершаем процесс: {exe_path} (PID: {proc.info['pid']})")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger_ui.error(
                f"Ошибка при обработке процесса {proc.info.get('pid')}: {str(e)}")
# Классы UI


class PLogAdapter:
    """Адаптер для логирования P"""

    def __init__(self, tab):
        self.tab = tab

    def log(self, message, message_type="info"):
        color_map = {
            "success": "green",
            "error": "red",
            "warning": "orange",
            "info": "black"
        }
        color = color_map.get(message_type, "black")
        self.tab.log_signal.emit(f"{message}", color)


class WorkerThread(QThread):
    log_signal = pyqtSignal(str, str, str)  # system, message, color
    finished = pyqtSignal()
    time_update = pyqtSignal(str)  # Для обновления времени до 09:15
    check_started = pyqtSignal(str, str)  # system, check_name
    check_finished = pyqtSignal(str, str, bool)  # system, check_name, success

    def __init__(self, system, checks, include_powerbi=False):
        super().__init__()
        self.system = system
        self.checks = checks
        self.include_powerbi = include_powerbi
        self.is_running = True

    def run(self):
        try:
            for check in self.checks:
                if not self.is_running:
                    break
                if "PowerBi" in check and not self.include_powerbi:
                    continue
                # Сигнал о начале проверки
                self.check_started.emit(self.system, check)
                self.log_signal.emit(
                    self.system, f"Начало проверки: {check}", "black")
                # Эмуляция выполнения проверки
                time.sleep(1)  # Имитация работы
                # Специальная обработка для PowerBi
                if "PowerBi" in check:
                    self.log_signal.emit(
                        self.system, "Ожидание 09:15 для запуска PowerBi...", "black")
                    self.wait_for_time(dt_time(9, 15))
                    self.log_signal.emit(
                        self.system, "Время 09:15 достигнуто! Запуск PowerBi...", "black")
                    time.sleep(2)
                # Генерация результата (случайно успешный или с ошибкой)
                success = random.choice(
                    [True, True, True, False])  # 75% успеха
                status = "Успешно" if success else "ОШИБКА"
                color = "red" if not success else "green"
                # Сигнал о завершении проверки
                self.check_finished.emit(self.system, check, success)
                self.log_signal.emit(
                    self.system, f"Завершено: {check} — {status}", color)
        except Exception as e:
            self.log_signal.emit(self.system, f"[ОШИБКА] {str(e)}", "red")
        finally:
            self.finished.emit()

    def wait_for_time(self, target_time):
        # Однократно пишем в лог о начале ожидания
        self.log_signal.emit(
            self.system, "Ожидание 09:15 для запуска PowerBi...", "black")
        while self.is_running:
            current_time = datetime.now().time()
            if current_time >= target_time:
                return
            # Рассчитываем оставшееся время
            now = datetime.now()
            target_datetime = datetime(
                now.year, now.month, now.day, target_time.hour, target_time.minute)
            if now > target_datetime:
                target_datetime = target_datetime.replace(day=now.day + 1)
            delta = target_datetime - now
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02d}:{minutes:02d}"
            # Обновляем только счетчик, не пишем в лог
            self.time_update.emit(time_str)
            # Увеличиваем интервал проверки до 10 секунд
            time.sleep(10)

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class AWorker(QThread):
    """Специальный воркер для проверок А"""
    finished = pyqtSignal()
    log_signal = pyqtSignal(str, str)  # message, color
    check_finished = pyqtSignal(str, bool)  # check_name, success
    check_started = pyqtSignal(str)  # check_name

    def __init__(self, tab, functions):
        super().__init__()
        self.tab = tab
        self.functions = functions  # Список кортежей (check_name, func)
        self.is_running = True
        self.log_adapter = PLogAdapter(tab)

    def run(self):
        try:
            with systems_lock:
                # Инициализируем логирование для A
                a.init_logging(self.log_adapter.log)
                for check_name, func in self.functions:
                    if not self.is_running:
                        break
                    self.check_started.emit(check_name)
                    # Логируем начало проверки
                    self.log_signal.emit(
                        f"Начало проверки: {check_name}", "black")
                    # Выполняем проверку и гарантируем булево возвращаемое значение
                    try:
                        result = func()
                        success = bool(result) if result is not None else False
                    except Exception as e:
                        self.log_signal.emit(
                            f"Ошибка при выполнении {check_name}: {str(e)}", "red")
                        success = False
                    # Логируем результат
                    status = "Успешно" if success else "ОШИБКА"
                    color = "green" if success else "red"
                    self.log_signal.emit(
                        f"Завершено: {check_name} — {status}", color)
                    # Отправляем сигнал о завершении
                    self.check_finished.emit(check_name, success)
        except Exception as e:
            self.log_signal.emit(f"[ОШИБКА] {str(e)}", "red")
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class PWorker(QThread):
    """Специальный воркер для проверок П"""
    finished = pyqtSignal()
    log_signal = pyqtSignal(str, str)  # message, color
    check_finished = pyqtSignal(str, bool)  # check_name, success
    check_started = pyqtSignal(str)  # check_name

    def __init__(self, tab, functions):
        super().__init__()
        self.tab = tab
        self.functions = functions  # Список кортежей (check_name, func)
        self.is_running = True
        self.log_adapter = PLogAdapter(tab)

    def run(self):
        try:
            with systems_lock:
                # Инициализируем логирование для P
                p.init_logging(self.log_adapter.log)
                for check_name, func in self.functions:
                    if not self.is_running:
                        break
                    self.check_started.emit(check_name)
                    # Логируем начало проверки
                    self.log_signal.emit(
                        f"Начало проверки: {check_name}", "black")
                    # Для проверки PowerBi дополнительно логируем время ожидания
                    if check_name == "Проверка PowerBi":
                        now = datetime.now()
                        target_time = dt_time(9, 15)
                        target_datetime = datetime(
                            now.year, now.month, now.day, target_time.hour, target_time.minute)
                        if now > target_datetime:
                            target_datetime = target_datetime.replace(
                                day=now.day + 1)
                        delta = target_datetime - now
                        total_minutes = delta.seconds // 60
                        self.log_signal.emit(
                            f"Ожидание запуска PowerBi: до 09:15 осталось {total_minutes} минут", "black")
                    # Выполняем проверку
                    success = func()
                    # Логируем результат
                    status = "Успешно" if success else "ОШИБКА"
                    color = "green" if success else "red"
                    self.log_signal.emit(
                        f"Завершено: {check_name} — {status}", color)
                    # Отправляем сигнал о завершении
                    self.check_finished.emit(check_name, success)
        except Exception as e:
            self.log_signal.emit(f"[ОШИБКА] {str(e)}", "red")
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class MiWorker(QThread):
    """Специальный воркер для проверок МИ"""
    finished = pyqtSignal()
    log_signal = pyqtSignal(str, str)  # message, color
    check_finished = pyqtSignal(str, bool)  # check_name, success
    check_started = pyqtSignal(str)  # check_name

    def __init__(self, tab, functions):
        super().__init__()
        self.tab = tab
        self.functions = functions  # Список кортежей (check_name, func)
        self.is_running = True
        self.log_adapter = PLogAdapter(tab)

    def run(self):
        try:
            with systems_lock:  # Используем лок для М, если нужен
                # Инициализируем логирование для М
                mi.init_logging(self.log_adapter.log)
                for check_name, func in self.functions:
                    if not self.is_running:
                        break
                    self.check_started.emit(check_name)
                    # Логируем начало проверки
                    self.log_signal.emit(
                        f"Начало проверки: {check_name}", "black")
                    # Выполняем проверку и гарантируем булево возвращаемое значение
                    try:
                        result = func()
                        success = bool(result) if result is not None else False
                    except Exception as e:
                        self.log_signal.emit(
                            f"Ошибка при выполнении {check_name}: {str(e)}", "red")
                        success = False
                    # Логируем результат
                    status = "Успешно" if success else "ОШИБКА"
                    color = "green" if success else "red"
                    self.log_signal.emit(
                        f"Завершено: {check_name} — {status}", color)
                    # Отправляем сигнал о завершении
                    self.check_finished.emit(check_name, success)
        except Exception as e:
            self.log_signal.emit(f"[ОШИБКА] {str(e)}", "red")
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class MWorker(QThread):
    """Специальный воркер для проверок М"""
    finished = pyqtSignal()
    log_signal = pyqtSignal(str, str)  # message, color
    check_finished = pyqtSignal(str, bool)  # check_name, success
    check_started = pyqtSignal(str)  # check_name

    def __init__(self, tab, functions):
        super().__init__()
        self.tab = tab
        self.functions = functions
        self.is_running = True
        self.log_adapter = PLogAdapter(tab)

    def run(self):
        try:
            with systems_lock:
                # Инициализируем логирование для М
                m.init_logging(self.log_adapter.log)
                for check_name, func in self.functions:
                    if not self.is_running:
                        break
                    self.check_started.emit(check_name)
                    self.log_signal.emit(
                        f"Начало проверки: {check_name}", "black")
                    try:
                        result = func()
                        success = bool(result) if result is not None else False
                    except Exception as e:
                        self.log_signal.emit(
                            f"Ошибка при выполнении {check_name}: {str(e)}", "red")
                        success = False
                    status = "Успешно" if success else "ОШИБКА"
                    color = "green" if success else "red"
                    self.log_signal.emit(
                        f"Завершено: {check_name} — {status}", color)
                    self.check_finished.emit(check_name, success)
        except Exception as e:
            self.log_signal.emit(f"[ОШИБКА] {str(e)}", "red")
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class GWorker(QThread):
    """Специальный воркер для проверок G"""
    finished = pyqtSignal()
    log_signal = pyqtSignal(str, str)
    check_finished = pyqtSignal(str, bool)
    check_started = pyqtSignal(str)

    def __init__(self, tab, functions):
        super().__init__()
        self.tab = tab
        self.functions = functions
        self.is_running = True
        self.log_adapter = PLogAdapter(tab)

    def run(self):
        try:
            with systems_lock:
                # Инициализируем логирование для G
                g.init_logging(self.log_adapter.log)
                for check_name, func in self.functions:
                    if not self.is_running:
                        break
                    self.check_started.emit(check_name)
                    self.log_signal.emit(
                        f"Начало проверки: {check_name}", "black")
                    try:
                        result = func()
                        success = bool(result) if result is not None else False
                    except Exception as e:
                        self.log_signal.emit(
                            f"Ошибка при выполнении {check_name}: {str(e)}", "red")
                        success = False
                    status = "Успешно" if success else "ОШИБКА"
                    color = "green" if success else "red"
                    self.log_signal.emit(
                        f"Завершено: {check_name} — {status}", color)
                    self.check_finished.emit(check_name, success)
        except Exception as e:
            self.log_signal.emit(f"[ОШИБКА] {str(e)}", "red")
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class KWorker(QThread):
    """Специальный воркер для проверок K"""
    finished = pyqtSignal()
    log_signal = pyqtSignal(str, str)
    check_finished = pyqtSignal(str, bool)
    check_started = pyqtSignal(str)

    def __init__(self, tab, functions):
        super().__init__()
        self.tab = tab
        self.functions = functions
        self.is_running = True
        self.log_adapter = PLogAdapter(tab)

    def run(self):
        try:
            with systems_lock:
                # Инициализируем логирование для K
                k.init_logging(self.log_adapter.log)
                for check_name, func in self.functions:
                    if not self.is_running:
                        break
                    self.check_started.emit(check_name)
                    self.log_signal.emit(
                        f"Начало проверки: {check_name}", "black")
                    try:
                        result = func()
                        success = bool(result) if result is not None else False
                    except Exception as e:
                        self.log_signal.emit(
                            f"Ошибка при выполнении {check_name}: {str(e)}", "red")
                        success = False
                    status = "Успешно" if success else "ОШИБКА"
                    color = "green" if success else "red"
                    self.log_signal.emit(
                        f"Завершено: {check_name} — {status}", color)
                    self.check_finished.emit(check_name, success)
        except Exception as e:
            self.log_signal.emit(f"[ОШИБКА] {str(e)}", "red")
        finally:
            self.finished.emit()

        def stop(self):
            self.is_running = False
            self.quit()
            self.wait()


class CheckItemWidget(QFrame):
    def __init__(self, check_name, parent=None):
        super().__init__(parent)
        self.check_name = check_name
        self.init_ui()
        self.apply_styles()
        self.set_status("default")

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        # Смайлик статуса
        self.status_icon = QLabel(STATUS_ICONS["default"])
        self.status_icon.setFont(QFont("Segoe UI", 12))
        self.status_icon.setFixedWidth(30)
        self.status_icon.setAlignment(Qt.AlignCenter)
        # Название проверки
        self.name_label = QLabel(self.check_name)
        font = QFont("Segoe UI", 12)  # Создаем объект шрифта
        font.setBold(True)  # Делаем шрифт жирным
        self.name_label.setFont(font)  # Применяем шрифт
        self.name_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        # Кнопка проверки
        self.check_button = QPushButton("Проверить")
        self.check_button.setFixedWidth(80)
        self.check_button.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.status_icon)
        layout.addWidget(self.name_label)
        layout.addWidget(self.check_button)
        self.setLayout(layout)
        self.setFixedHeight(45)

    def apply_styles(self):
        apply_style(self, "CheckItemWidget", COLORS)

    def set_status(self, status):
        """Устанавливает статус проверки: default, running, success, error"""
        self.status_icon.setText(STATUS_ICONS.get(
            status, STATUS_ICONS["default"]))
        # Изменяем цвет смайлика в зависимости от статуса
        if status == "running":
            self.status_icon.setStyleSheet("color: #ff9800;")  # Оранжевый
        elif status == "success":
            self.status_icon.setStyleSheet("color: #4caf50;")  # Зеленый
        elif status == "error":
            self.status_icon.setStyleSheet("color: #e53935;")  # Красный
        else:
            self.status_icon.setStyleSheet("color: #b0bec5;")  # Серый


class LogListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        apply_style(self, "LogListWidget", COLORS)
        self.setWordWrap(True)
        # Настройка шрифта
        font = QFont("Consolas", 11)
        self.setFont(font)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                clipboard = QApplication.clipboard()
                clipboard.setText(item.text())
                # Анимация подсветки
                self.highlight_item(item)
        super().mousePressEvent(event)

    def highlight_item(self, item):
        original_brush = item.background()
        item.setBackground(QBrush(QColor(COLORS['log_selected'])))
        QTimer.singleShot(300, lambda: item.setBackground(original_brush))


class SystemTab(QWidget):
    update_check_status = pyqtSignal(str, str)  # check_name, status
    log_signal = pyqtSignal(str, str)  # message, color

    def __init__(self, system_name, checks):
        super().__init__()
        self.system_name = system_name
        self.checks = checks
        self.worker = None
        self.p_worker = None
        self.a_worker = None
        self.emulation_worker = None
        self.check_widgets = {}
        self.powerbi_timer = None  # Таймер для обновления счетчика
        self.is_checking = False  # Флаг для отслеживания состояния проверки
        self.init_ui()
        # Для системы А создаем маппинг функций
        if system_name == "А":
            self.a_functions = {
                "Проверка мониторинга": a.monitoring,
                "Проверка пользователей online": a.usersOnline,
                "Проверка адаптера А": a.adapterCheck,
                "Проверка логов адаптера А": a.check_errors_in_log_adapter
            }
        # Для системы М
        if system_name == "М":
            self.m_functions = {
                "Проверка API шлюза": m.test,
                "Проверка шифрования": m.test,
                "Проверка очередей": m.test
            }
        # Для системы МИ создаем маппинг функций
        if system_name == "МИ":
            self.mi_functions = {
                "Приложение АС": mi.test,
                "Мониторинг служб": m.test,
                "Проверка доступности сайта": mi.test,
                "Проверка доступности служб": mi.test
            }
        # Для системы П создаем маппинг функций
        if system_name == "П":
            self.p_functions = {
                "Проверка доступности ссылок": p.test,
                "Проверка адаптера": p.test,
                "Проверка логов Elastic": p.test,
                "Проверка PowerBi": p.test
            }
        # Для системы G
        if system_name == "G":
            self.g_functions = {
                "Проверка сервисов системы": g.test,
                "Проверка нагрузки на сервера": g.test
            }
        # Для системы K
        if system_name == "K":
            self.k_functions = {
                "Проверка топиков": k.test,
                "Проверка потребителей": k.test,
                "Проверка задержек": k.test
            }
        # Подключаем сигнал обновления статуса
        self.update_check_status.connect(self.update_check_status_handler)
        self.log_signal.connect(self.add_log)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        # Список проверок в один столбец
        checks_frame = QWidget()
        checks_frame.setStyleSheet("background-color: white;")
        checks_layout = QVBoxLayout(checks_frame)
        checks_layout.setContentsMargins(10, 10, 10, 10)
        checks_layout.setSpacing(5)
        # Создаем виджеты для каждой проверки
        for check in self.checks:
            widget = CheckItemWidget(check)
            self.check_widgets[check] = widget
            checks_layout.addWidget(widget)
        checks_layout.addStretch()
        main_layout.addWidget(checks_frame, 1)
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.btn_check_all = QPushButton("Проверить всё")
        self.btn_check_all.setFont(QFont("Segoe UI", 10))
        self.btn_check_all.setMinimumHeight(40)
        if self.system_name == "П":
            self.btn_check_powerbi = QPushButton("Проверить всё + PowerBi")
            self.btn_check_powerbi.setFont(QFont("Segoe UI", 10))
            self.btn_check_powerbi.setMinimumHeight(40)
            buttons_layout.addWidget(self.btn_check_powerbi)
        buttons_layout.addWidget(self.btn_check_all)
        buttons_layout.addStretch()
        self.btn_copy = QPushButton("Копировать логи")
        self.btn_copy.setFont(QFont("Segoe UI", 10))
        self.btn_copy.setMinimumHeight(40)
        buttons_layout.addWidget(self.btn_copy)
        self.btn_clear = QPushButton("Очистить логи")
        self.btn_clear.setFont(QFont("Segoe UI", 10))
        self.btn_clear.setMinimumHeight(40)
        buttons_layout.addWidget(self.btn_clear)
        main_layout.addLayout(buttons_layout)
        # Логи выполнения с отдельным счетчиком
        log_frame = QFrame()
        log_frame.setStyleSheet(
            f"background-color: white; border-radius: 5px; border: 1px solid {COLORS['border']};")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(10, 10, 10, 10)
        # Заголовок с счетчиком
        log_header_layout = QHBoxLayout()
        log_label = QLabel("<b>Логи выполнения:</b>")
        log_label.setFont(QFont("Segoe UI", 11))
        log_header_layout.addWidget(log_label)
        # Счетчик времени до Power BI
        self.powerbi_counter = QLabel("")
        self.powerbi_counter.setFont(QFont("Segoe UI", 10))
        self.powerbi_counter.setStyleSheet(
            f"color: {COLORS['warning']}; font-weight: bold;")
        self.powerbi_counter.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        log_header_layout.addWidget(self.powerbi_counter)
        log_header_layout.setStretch(0, 3)  # Заголовок занимает 3 части
        log_header_layout.setStretch(1, 1)  # Счетчик занимает 1 часть
        log_layout.addLayout(log_header_layout)
        self.log_output = LogListWidget()
        log_layout.addWidget(self.log_output, 1)
        main_layout.addWidget(log_frame, 3)
        self.setLayout(main_layout)
        self.apply_styles()
        # Подключаем сигналы
        for check in self.checks:
            self.check_widgets[check].check_button.clicked.connect(
                lambda _, c=check: self.run_single_check(c)
            )
        self.btn_check_all.clicked.connect(
            lambda: self.run_all_checks(include_powerbi=False))
        if self.system_name == "П":
            self.btn_check_powerbi.clicked.connect(
                lambda: self.run_all_checks(include_powerbi=True))
        self.btn_copy.clicked.connect(self.copy_logs)
        self.btn_clear.clicked.connect(self.clear_logs)

    def apply_styles(self):
        """Применяет стили к виджету"""
        apply_style(self, "SystemTab", COLORS)

    def update_check_status_handler(self, check_name, status):
        """Обработчик обновления статуса проверки"""
        try:
            if check_name in self.check_widgets:
                self.check_widgets[check_name].set_status(status)
        except Exception as e:
            print(f"Ошибка в update_check_status_handler: {e}")

    def add_log(self, message, color="black"):
        """Добавляет запись в лог"""
        try:
            item = QListWidgetItem(message)
            if color == "red":
                item.setForeground(QColor(COLORS['error']))
            elif color == "green":
                item.setForeground(QColor(COLORS['success']))
            elif color == "orange":
                item.setForeground(QColor(COLORS['warning']))
            else:
                item.setForeground(QColor(COLORS['text']))
            self.log_output.addItem(item)
            self.log_output.scrollToBottom()
        except Exception as e:
            print(f"Ошибка в add_log: {e}")

    def update_powerbi_counter(self):
        """Обновляет счетчик времени до 09:15"""
        try:
            now = datetime.now()
            target_time = dt_time(9, 15)
            # Если уже прошло 09:15, показываем 00:00
            if now.time() >= target_time:
                self.powerbi_counter.setText("До проверки осталось: 00:00")
                if self.powerbi_timer:
                    self.powerbi_timer.stop()
                return
            # Рассчитываем оставшееся время
            target_datetime = datetime(
                now.year, now.month, now.day, target_time.hour, target_time.minute)
            delta = target_datetime - now
            # Форматируем время в ЧЧ:ММ
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            time_str = f"До проверки осталось: {hours:02d}:{minutes:02d}"
            self.powerbi_counter.setText(time_str)
        except Exception as e:
            print(f"Ошибка в update_powerbi_counter: {e}")

    def start_powerbi_timer(self):
        """Запускает таймер для обновления счетчика"""
        try:
            # Останавливаем предыдущий таймер, если он был
            if self.powerbi_timer:
                self.powerbi_timer.stop()
            # Создаем новый таймер
            self.powerbi_timer = QTimer()
            self.powerbi_timer.timeout.connect(self.update_powerbi_counter)
            self.powerbi_timer.start(60000)  # Обновляем каждую минуту
            # Сразу обновляем счетчик
            self.update_powerbi_counter()
        except Exception as e:
            print(f"Ошибка в start_powerbi_timer: {e}")

    def stop_powerbi_timer(self):
        """Останавливает таймер счетчика"""
        try:
            if self.powerbi_timer:
                self.powerbi_timer.stop()
                self.powerbi_timer = None
            self.powerbi_counter.setText("")
        except Exception as e:
            print(f"Ошибка в stop_powerbi_timer: {e}")

    def run_single_check(self, check_name):
        """Запускает одиночную проверку"""
        try:
            if self.is_checking:
                self.add_log(
                    "Уже выполняется проверка. Дождитесь завершения.", "orange")
                return
            self.is_checking = True
            self.toggle_buttons(False)
            self.stop_powerbi_timer()
            # Обработчики для разных систем
            system_workers = {
                "А": ("a_functions", "a_worker", AWorker),
                "М": ("m_functions", "m_worker", MWorker),
                "МИ": ("mi_functions", "mi_worker", MiWorker),
                "П": ("p_functions", "p_worker", PWorker),
                "G": ("g_functions", "g_worker", GWorker),
                "K": ("k_functions", "k_worker", KWorker)
            }
            if self.system_name in system_workers:
                functions_attr, worker_attr, worker_class = system_workers[self.system_name]
                functions_dict = getattr(self, functions_attr, {})
                if check_name in functions_dict:
                    func = functions_dict[check_name]
                    worker = worker_class(self, [(check_name, func)])
                    # Подключаем сигналы
                    worker.log_signal.connect(
                        lambda msg, color: self.add_log(msg, color))
                    worker.check_started.connect(
                        lambda cn: self.update_check_status.emit(cn, "running")
                    )
                    worker.check_finished.connect(
                        lambda cn, success: self.update_check_status.emit(
                            cn, "success" if success else "error"
                        )
                    )
                    worker.finished.connect(self.on_single_check_finished)
                    # Сохраняем worker и запускаем
                    setattr(self, worker_attr, worker)
                    worker.start()
                    return
            # Для систем без специальных обработчиков используем эмуляцию
            self.update_check_status.emit(check_name, "running")
            self.add_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] Начало проверки: {check_name}", "black")
            self.emulation_worker = EmulationWorker(check_name)
            self.emulation_worker.finished.connect(
                lambda success, cn: self.on_emulation_finished(success, cn)
            )
            self.emulation_worker.start()
        except Exception as e:
            print(f"Ошибка в run_single_check: {e}")
            self.is_checking = False
            self.toggle_buttons(True)

    def on_emulation_finished(self, success, check_name):
        """Обработчик завершения эмуляции проверки"""
        try:
            status = "Успешно" if success else "ОШИБКА"
            color = "red" if not success else "green"
            # Обновляем статус
            self.update_check_status.emit(
                check_name, "success" if success else "error")
            self.add_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] Завершено: {check_name} — {status}", color)
            self.is_checking = False
            self.toggle_buttons(True)
            self.emulation_worker = None
        except Exception as e:
            print(f"Ошибка в on_emulation_finished: {e}")
            self.is_checking = False
            self.toggle_buttons(True)

    def run_all_checks(self, include_powerbi):
        """Запускает все проверки"""
        try:
            if self.is_checking:
                self.add_log(
                    "Уже выполняется проверка. Дождитесь завершения.", "orange")
                return
            self.is_checking = True
            self.toggle_buttons(False)
            self.stop_powerbi_timer()
            # Сбрасываем все статусы
            for check in self.checks:
                self.update_check_status.emit(check, "default")
            self.log_output.clear()
            # Обработчики для разных систем
            system_configs = {
                "А": ("a_functions", "a_worker", AWorker),
                "П": ("p_functions", "p_worker", PWorker),
                "МИ": ("mi_functions", "mi_worker", MWorker),
                "М": ("m_functions", "m_worker", MiWorker),
                "G": ("g_functions", "g_worker", GWorker),
                "K": ("k_functions", "k_worker", KWorker)
            }
            if self.system_name in system_configs:
                functions_attr, worker_attr, worker_class = system_configs[self.system_name]
                functions_dict = getattr(self, functions_attr, {})
                # ОСОБАЯ ОБРАБОТКА ДЛЯ П
                if self.system_name == "П":
                    self.add_log(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Запуск {'полной ' if include_powerbi else ''}проверки системы П...",
                        "black")
                    # Запускаем таймер, если включена проверка PowerBi
                    if include_powerbi:
                        self.start_powerbi_timer()
                    # Создаем список функций для проверки
                    functions = [
                        ("Проверка доступности ссылок", p.test),
                        ("Проверка адаптера", p.test),
                        ("Проверка логов ИСМ (Elastic)", p.test)
                    ]
                    # Добавляем PowerBi только если include_powerbi=True
                    if include_powerbi:
                        functions.append(
                            ("Проверка PowerBi", self.wait_and_run_powerbi))
                    # Создаем воркер
                    self.p_worker = PWorker(self, functions)
                    self.p_worker.log_signal.connect(
                        lambda msg, color: self.add_log(msg, color))
                    self.p_worker.check_started.connect(
                        lambda check_name: self.update_check_status.emit(
                            check_name, "running")
                    )
                    self.p_worker.check_finished.connect(
                        lambda cn, success: self.update_check_status.emit(
                            cn, "success" if success else "error")
                    )
                    self.p_worker.finished.connect(self.on_checks_finished)
                    self.p_worker.start()
                else:
                    # Для других систем используем стандартный подход
                    self.add_log(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Запуск проверки системы {self.system_name}...",
                        "black")
                    functions_list = list(functions_dict.items())
                    worker = worker_class(self, functions_list)
                    # Подключаем сигналы
                    worker.log_signal.connect(
                        lambda msg, color: self.add_log(msg, color))
                    worker.check_started.connect(
                        lambda cn: self.update_check_status.emit(cn, "running")
                    )
                    worker.check_finished.connect(
                        lambda cn, success: self.update_check_status.emit(
                            cn, "success" if success else "error"
                        )
                    )
                    worker.finished.connect(self.on_checks_finished)
                    # Сохраняем worker и запускаем
                    setattr(self, worker_attr, worker)
                    worker.start()
            else:
                # Для систем без специальных обработчиков используем эмуляцию
                self.add_log(f"[{datetime.now().strftime('%H:%M:%S')}] Запуск проверки системы {self.system_name}...",
                             "black")
                checks_to_run = self.checks.copy()
                if not include_powerbi:
                    checks_to_run = [
                        c for c in checks_to_run if "PowerBi" not in c]
                self.worker = WorkerThread(
                    self.system_name, checks_to_run, include_powerbi)
                self.worker.log_signal.connect(self.add_thread_log)
                self.worker.finished.connect(self.on_checks_finished)
                self.worker.time_update.connect(
                    lambda msg: self.add_log(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", "black"))
                self.worker.check_started.connect(self.on_check_started)
                self.worker.check_finished.connect(self.on_check_finished)
                self.worker.start()
        except Exception as e:
            print(f"Ошибка в run_all_checks: {e}")
            self.is_checking = False
            self.toggle_buttons(True)

    def wait_and_run_powerbi(self):
        """Ожидает 09:15 и выполняет проверку PowerBi"""
        try:
            # Ожидаем 09:15 без спама в лог
            target_time = dt_time(9, 15)
            while True:
                # Проверяем, не была ли остановлена проверка
                if not self.is_checking:
                    return False
                current_time = datetime.now().time()
                if current_time >= target_time:
                    break
                # Спим 10 секунд вместо 1, чтобы уменьшить нагрузку
                time.sleep(10)
            # Выполняем проверку PowerBi
            return p.test()
        except Exception as e:
            print(f"Ошибка в wait_and_run_powerbi: {e}")
            return False

    def on_check_started(self, system, check_name):
        try:
            if system == self.system_name:
                self.update_check_status.emit(check_name, "running")
        except Exception as e:
            print(f"Ошибка в on_check_started: {e}")

    def on_check_finished(self, system, check_name, success):
        try:
            if system == self.system_name:
                self.update_check_status.emit(
                    check_name, "success" if success else "error")
        except Exception as e:
            print(f"Ошибка в on_check_finished: {e}")

    def add_thread_log(self, system, message, color):
        try:
            if system == self.system_name:
                # Пропускаем сообщения о времени до PowerBi, так как у нас теперь есть отдельный счетчик
                if "До запуска PowerBi" not in message:
                    self.add_log(message, color)
        except Exception as e:
            print(f"Ошибка в add_thread_log: {e}")

    def on_checks_finished(self):
        """Обработчик завершения всех проверок"""
        try:
            # Останавливаем таймер при завершении проверок
            self.stop_powerbi_timer()
            # Проверяем наличие воркеров перед обращением к ним
            if self.worker is not None:
                self.add_log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] {'Полная ' if self.worker.include_powerbi else ''}проверка системы {self.system_name} завершена",
                    "black")
                self.worker = None
            if self.p_worker is not None:
                self.add_log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Проверка системы П завершена", "black")
                self.p_worker = None
            if self.a_worker is not None:  # Проверяем, что a_worker существует
                self.add_log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Проверка системы А завершена", "black")
                self.a_worker = None
            self.is_checking = False
            self.toggle_buttons(True)
        except Exception as e:
            print(f"Ошибка в on_checks_finished: {e}")
            self.is_checking = False
            self.toggle_buttons(True)

    def on_single_check_finished(self):
        """Обработчик завершения одиночной проверки"""
        try:
            # Останавливаем таймер при завершении проверки
            self.stop_powerbi_timer()
            self.p_worker = None
            self.a_worker = None
            self.is_checking = False
            self.toggle_buttons(True)
        except Exception as e:
            print(f"Ошибка в on_single_check_finished: {e}")
            self.is_checking = False
            self.toggle_buttons(True)

    def stop_all_workers(self):
        """Останавливает все рабочие потоки"""
        try:
            self.stop_powerbi_timer()
            self.is_checking = False
            workers_to_stop = [
                'worker', 'p_worker', 'a_worker', 'mi_worker',
                'm_worker', 'g_worker', 'k_worker', 'emulation_worker'
            ]
            for worker_name in workers_to_stop:
                worker = getattr(self, worker_name, None)
                if worker and worker.isRunning():
                    worker.stop()
        except Exception as e:
            print(f"Ошибка в stop_all_workers: {e}")

    def toggle_buttons(self, enabled):
        """Включает/отключает кнопки управления и вкладки систем"""
        try:
            self.btn_check_all.setEnabled(enabled)
            self.btn_copy.setEnabled(enabled)
            self.btn_clear.setEnabled(enabled)
            if self.system_name == "П":
                self.btn_check_powerbi.setEnabled(enabled)
            for check in self.checks:
                self.check_widgets[check].check_button.setEnabled(enabled)
            # Блокируем/разблокируем вкладки систем в главном окне
            if hasattr(self, 'main_window') and self.main_window:
                self.main_window.set_tabs_enabled(enabled)
        except Exception as e:
            print(f"Ошибка в toggle_buttons: {e}")

    def copy_logs(self):
        """Копирует логи в буфер обмена"""
        try:
            all_text = "\n".join([self.log_output.item(i).text()
                                  for i in range(self.log_output.count())])
            clipboard = QApplication.clipboard()
            clipboard.setText(all_text)
            # Анимация кнопки копирования
            self.animate_button(self.btn_copy)
        except Exception as e:
            print(f"Ошибка в copy_logs: {e}")

    def animate_button(self, button):
        """Анимирует кнопку при нажатии"""
        try:
            original_style = button.styleSheet()
            button.setStyleSheet(
                f"background-color: {COLORS['success']}; color: white;")
            QTimer.singleShot(
                300, lambda: button.setStyleSheet(original_style))
        except Exception as e:
            print(f"Ошибка в animate_button: {e}")

    def clear_logs(self):
        """Очищает логи"""
        try:
            self.log_output.clear()
            # Анимация кнопки очистки
            self.animate_button(self.btn_clear)
        except Exception as e:
            print(f"Ошибка в clear_logs: {e}")


class EmulationWorker(QThread):
    """Воркер для эмуляции проверки"""
    finished = pyqtSignal(bool, str)  # success, check_name

    def __init__(self, check_name):
        super().__init__()
        self.check_name = check_name
        self.is_running = True

    def run(self):
        try:
            # Эмуляция выполнения проверки
            time.sleep(1)  # Имитация работы
            # Генерация результата (случайно успешный или с ошибкой)
            success = random.choice([True, False])
            # Отправляем результат
            self.finished.emit(success, self.check_name)
        except Exception as e:
            self.finished.emit(False, self.check_name)

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()


class TokenDialog(QDialog):
    def __init__(self, token, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JIRA Token")
        self.setModal(True)
        self.token = token
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        # Токен
        token_label = QLabel("Ваш JIRA токен:")
        token_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(token_label)
        self.token_edit = QLineEdit(self.token)
        self.token_edit.setReadOnly(True)
        layout.addWidget(self.token_edit)
        # Кнопка копирования
        copy_btn = QPushButton("Копировать токен")
        copy_btn.clicked.connect(self.copy_token)
        layout.addWidget(copy_btn)
        # Кнопка установки в переменные среды
        set_env_btn = QPushButton("Установить переменную среды автоматически")
        set_env_btn.clicked.connect(self.set_environment_variable)
        layout.addWidget(set_env_btn)
        # Инструкция
        instruction_label = QLabel("Инструкция по установке:")
        instruction_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(instruction_label)
        instructions = QLabel(
            "Если автоматическая установка не работает, выполните вручную:\n"
            "1. Скопируйте токен выше\n"
            "2. ПКМ по 'Этот компьютер'\n"
            "3. Дополнительные параметры системы\n"
            "4. Переменные среды\n"
            "5. Измените переменную с именем JIRATOKEN\n"
            "6. Вставьте скопированный токен в значение"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def copy_token(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.token)
        QMessageBox.information(
            self, "Успех", "Токен скопирован в буфер обмена")

    def set_environment_variable(self):
        if set_environment_variable('JIRATOKEN', self.token):
            QMessageBox.information(self, "Успех",
                                    "Переменная среды JIRATOKEN успешно обновлена!\n"
                                    "Изменения вступят в силу для новых процессов.")
        else:
            QMessageBox.warning(self, "Ошибка",
                                "Не удалось автоматически установить переменную среды.\n"
                                "Пожалуйста, выполните установку вручную по инструкции ниже.")


class PasswordDialog(QDialog):
    def __init__(self, system_name, parent=None):
        super().__init__(parent)
        self.system_name = system_name
        self.setWindowTitle(f"Настройки пароля - {system_name}")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        # Описание в зависимости от системы
        descriptions = {
            "А": "Пароль для системы А",
            "М": "Пароль для системы М",
            "МИ": "Пароль для системы МИ",
            "П": "Пароль для Elastic",
            "G": "Пароль для системы G",
            "Личный": "Личный пароль пользователя"
        }
        description = QLabel(descriptions.get(
            self.system_name, "Введите пароль"))
        layout.addWidget(description)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        # Кнопки OK и Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_password(self):
        return self.password_input.text()


class UsernamePasswordDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.description_label = QLabel("Введите логин и пароль")
        layout.addWidget(self.description_label)
        # Поле для логина
        layout.addWidget(QLabel("Логин:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)
        # Поле для пароля
        layout.addWidget(QLabel("Пароль:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        # Кнопки OK и Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def set_description(self, text):
        self.description_label.setText(text)

    def get_username(self):
        return self.username_input.text()

    def get_password(self):
        return self.password_input.text()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Checklist Validator")
        self.setGeometry(100, 100, 1000, 800)
        # Настройка центрального виджета
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 0)  # Убираем нижний отступ
        main_layout.setSpacing(10)
        # Создаем вкладки
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(False)
        self.tabs.setMovable(False)
        self.tab_widgets = {}
        # Настройка ширины вкладок
        font_metrics = QFontMetrics(QFont("Segoe UI", 10))
        for system in SYSTEMS_CONFIG.keys():
            width = font_metrics.width(system) + 45
            self.tabs.setStyleSheet(
                f"QTabBar::tab {{ min-width: {width}px; }}")
        for system, checks in SYSTEMS_CONFIG.items():
            tab = SystemTab(system, checks)
            tab.main_window = self  # Передаем ссылку на главное окно
            self.tabs.addTab(tab, system)
            self.tab_widgets[system] = tab
        # Вкладки занимают основное пространство
        main_layout.addWidget(self.tabs, 1)
        # Создаем нижний макет для кнопки настроек
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)  # Убираем все отступы
        # Кнопка настроек (шестеренка) в левом нижнем углу
        self.settings_button = QPushButton()
        self.settings_button.setFixedSize(30, 30)
        # Устанавливаем иконку ключа
        self.settings_button.setText("🔑")
        font = QFont("Segoe UI Symbol", 16)
        self.settings_button.setFont(font)
        self.settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 4px;
                /* Убираем margin-bottom */
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_hover']};
            }}
        """)
        self.settings_button.clicked.connect(self.show_settings_menu)
        # Добавляем кнопку в левую часть нижнего макета
        bottom_layout.addWidget(self.settings_button)
        # Добавляем отступ между кнопкой и ссылками
        bottom_layout.addSpacing(10)
        # Добавляем текст "Ссылки на инструкции:" перед ссылками
        instructions_label = QLabel("Ссылки на инструкции:")
        instructions_label.setStyleSheet(
            f"color: {COLORS['text']}; font-weight; font-size: 12pt;")
        bottom_layout.addWidget(instructions_label)
        # Небольшой отступ между текстом и ссылками
        bottom_layout.addSpacing(5)
        # Создаем виджет для гиперссылок
        links_widget = QWidget()
        links_layout = QVBoxLayout(links_widget)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(5)
        # Первый ряд ссылок
        first_row = QHBoxLayout()
        first_row.setSpacing(15)
        a_link = QLabel(
            '<a href="https://ya.ru/" style="color: %s; text-decoration: none;">А</a>' %
            COLORS['primary'])
        a_link.setOpenExternalLinks(True)
        a_link.setStyleSheet("font-size: 12pt;")
        first_row.addWidget(a_link)
        m_link = QLabel(
            '<a href="https://ya.ru/" style="color: %s; text-decoration: none;">М</a>' %
            COLORS['primary'])
        m_link.setOpenExternalLinks(True)
        m_link.setStyleSheet("font-size: 12pt;")
        first_row.addWidget(m_link)
        g_link = QLabel(
            '<a href="https://ya.ru/" style="color: %s; text-decoration: none;">Г</a>' %
            COLORS['primary'])
        g_link.setOpenExternalLinks(True)
        g_link.setStyleSheet("font-size: 12pt;")
        first_row.addWidget(g_link)
        links_layout.addLayout(first_row)
        p_link = QLabel(
            '<a href="https://ya.ru/" style="color: %s; text-decoration: none;">П</a>' %
            COLORS['primary'])
        p_link.setOpenExternalLinks(True)
        p_link.setStyleSheet("font-size: 12pt;")
        first_row.addWidget(p_link)
        mi_link = QLabel(
            '<a href="https://ya.ru/" style="color: %s; text-decoration: none;">МИ</a>' %
            COLORS['primary'])
        mi_link.setOpenExternalLinks(True)
        mi_link.setStyleSheet("font-size: 12pt;")
        first_row.addWidget(mi_link)
        k_link = QLabel(
            '<a href="https://ya.ru/" style="color: %s; text-decoration: none;">K</a>' %
            COLORS['primary'])
        k_link.setOpenExternalLinks(True)
        k_link.setStyleSheet("font-size: 12pt;")
        self.description_label = QLabel("Инструкции:")
        first_row.addWidget(k_link)
        # Добавляем виджет с ссылками в нижний макет
        bottom_layout.addWidget(links_widget)
        # Добавляем растягивающееся пространство справа
        bottom_layout.addStretch()
        # Добавляем нижний макет в основной макет
        main_layout.addLayout(bottom_layout)
        # Статус бар
        self.status_bar = self.statusBar()
        # Добавляем progress_label в статус бар
        self.progress_label = QLabel("Готов")
        self.progress_label.setStyleSheet("color: green;")
        self.status_bar.addPermanentWidget(self.progress_label)
        # Меню настроек
        self.settings_menu = QMenu(self)
        # Добавляем пункты меню для каждой системы
        systems = ["А", "М", "П", "МИ", "G", "Личный"]
        for system in systems:
            action = QAction(system, self)
            action.triggered.connect(
                lambda checked, s=system: self.change_password(s))
            self.settings_menu.addAction(action)
        self.apply_styles()
        self.original_tab_style = self.tabs.styleSheet()
        self.current_tab_index = 0
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        """Запоминаем текущую активную вкладку"""
        self.current_tab_index = index

    def set_tabs_enabled(self, enabled):
        """Блокирует или разблокирует вкладки систем с сохранением позиции"""
        # Запоминаем текущую вкладку
        current_index = self.tabs.currentIndex()
        current_system = self.tabs.tabText(
            current_index) if current_index >= 0 else ""
        # Временно отключаем сигналы
        self.tabs.blockSignals(True)
        try:
            # Блокируем/разблокируем вкладки
            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, enabled)
            # Восстанавливаем текущую вкладку, если она доступна
            if enabled and current_system:
                # Восстанавливаем стиль
                self.tabs.setStyleSheet(self.original_tab_style)
                # Ищем вкладку с тем же именем системы
                for i in range(self.tabs.count()):
                    if self.tabs.tabText(i) == current_system:
                        self.tabs.setCurrentIndex(i)
                        break
                else:
                    # Если не нашли, переходим на первую доступную
                    self.tabs.setCurrentIndex(0)
            elif not enabled:
                # При блокировке оставляем текущую вкладку активной
                if 0 <= current_index < self.tabs.count():
                    self.tabs.setCurrentIndex(current_index)
            # Визуальные стили и обновление статуса
            if enabled:
                self.tabs.setStyleSheet(self.original_tab_style)
                if hasattr(self, 'progress_label'):
                    self.progress_label.setText("Готов")
                    self.progress_label.setStyleSheet("color: green;")
            else:
                self.tabs.setStyleSheet(f"""
                    QTabBar::tab:disabled {{
                        background-color: {COLORS['disabled']};
                        color: #757575;
                    }}
                    QTabBar::tab:selected {{
                        background-color: white;
                        color: {COLORS['primary']};
                        }}
                """)
                if hasattr(self, 'progress_label'):
                    self.progress_label.setText("Выполняется проверка...")
                    self.progress_label.setStyleSheet(
                        "color: orange; font-weight: bold;")
        finally:
            # Включаем сигналы обратно
            self.tabs.blockSignals(False)

    def show_settings_menu(self):
        apply_style(self.settings_menu, "SettingsMenu", COLORS)
        # Показываем меню рядом с кнопкой
        button_rect = self.settings_button.rect()
        button_pos = self.settings_button.mapToGlobal(button_rect.bottomLeft())
        # Показываем меню под кнопкой
        self.settings_menu.exec_(button_pos)

    def change_password(self, system_name):
        import base64
        if system_name == "П":
            self.change_p_passwords()
        elif system_name == "Личный":
            dialog = PasswordDialog(system_name, self)
            if dialog.exec_() == QDialog.Accepted:
                password = dialog.get_password()
                if password:
                    # Кодируем пароль в base64
                    encoded_token = base64.b64encode(
                        password.encode()).decode('utf-8')
                    # Устанавливаем переменную среды в текущем процессе
                    os.environ['JIRATOKEN'] = encoded_token
                    # Показываем диалог с токеном
                    token_dialog = TokenDialog(encoded_token, self)
                    token_dialog.exec_()
        else:
            dialog = PasswordDialog(system_name, self)
            if dialog.exec_() == QDialog.Accepted:
                password = dialog.get_password()
                if password:
                    keyring.set_password(
                        "ChecklistValidator", system_name, password)
                    QMessageBox.information(
                        self, "Успех", "Пароль успешно сохранен!")

    def change_p_passwords(self):
        # 1. Пароль для AdapterA
        dialog_a = PasswordDialog("AdapterA", self)
        dialog_a.setWindowTitle("AdapterA")
        if dialog_a.exec_() == QDialog.Accepted:
            pass_a = dialog_a.get_password()
            if pass_a:
                keyring.set_password("AdapterA", "admin", pass_a)
            else:
                QMessageBox.warning(
                    self, "Ошибка", "Пароль для AdapterA не введен")
                return
        # 2. Пароль для AdapterP
        dialog_p = PasswordDialog("AdapterP", self)
        dialog_p.setWindowTitle("AdapterP")
        if dialog_p.exec_() == QDialog.Accepted:
            pass_p = dialog_p.get_password()
            if pass_p:
                keyring.set_password("AdapterP", "admin", pass_p)
            else:
                QMessageBox.warning(
                    self, "Ошибка", "Пароль для AdapterP не введен")
                return
        # 3. Логин и пароль для Elastic
        dialog_elastic = PasswordDialog("Elastic", self)
        dialog_elastic.setWindowTitle("Elastic")
        if dialog_elastic.exec_() == QDialog.Accepted:
            login_elastic = dialog_elastic.get_username()
            pass_elastic = dialog_elastic.get_password()
            if login_elastic and pass_elastic:
                keyring.set_password("Elastic", login, pass_elastic)
            else:
                QMessageBox.warning(
                    self, "Ошибка", "Пароль для Elastic не введены")
                return
        QMessageBox.information(
            self, "Успех", "Все пароли для успешно сохранены!")

    def mousePressEvent(self, event):
        # Закрываем меню настроек при клике в любом месте основного окна
        if self.settings_menu.isVisible():
            self.settings_menu.hide()
        super().mousePressEvent(event)

    def apply_styles(self):
        apply_style(self, "MainWindow", COLORS)

    def closeEvent(self, event):
        # Создаем и запускаем поток для закрытия Chrome процессов
        chrome_thread = threading.Thread(
            target=self.cleanup_chrome_processes, daemon=True)
        chrome_thread.start()
        # Останавливаем все потоки приложения
        for tab in self.tab_widgets.values():
            tab.stop_all_workers()
            tab.log_output.clear()
            tab.toggle_buttons(True)
            # Сбрасываем статусы проверок
            for check in tab.checks:
                tab.update_check_status.emit(check, "default")
        # Ждем завершения потока с Chrome процессами (максимум 2 секунды)
        chrome_thread.join(2.0)
        # Закрываем основное приложение
        super().closeEvent(event)

    def cleanup_chrome_processes(self):
        """Асинхронное закрытие процессов Chrome"""
        try:
            close_driver()
        except Exception as e:
            print(f"Ошибка при очистке Chrome процессов: {e}")


def run_interface():
    time_s = time.time()
    # Настройка плагинов Qt для Windows
    if sys.platform == 'win32':
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = './venv/Lib/site-packages/PyQt5/Qt5/plugins'
    # Создание приложения
    app = QApplication(sys.argv)
    # Собираем стили для скроллбаров
    scrollbar_styles = []
    for key in styles:
        if key.startswith('scrollbar_'):
            scrollbar_styles.append(styles[key])
    # Применяем стили
    app_styles = " ".join(scrollbar_styles)
    app.setStyleSheet(app_styles)
    # Настройка глобальных стилей
    app.setStyle("Fusion")
    # Настройка шрифта для всего приложения
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    # Настройка палитры
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["background"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["log_background"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["background"]))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["primary"]))
    palette.setColor(QPalette.ToolTipText, QColor("white"))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["primary"]))
    palette.setColor(QPalette.ButtonText, QColor("white"))
    palette.setColor(QPalette.BrightText, QColor("red"))
    palette.setColor(QPalette.Highlight, QColor(COLORS["primary"]).lighter())
    palette.setColor(QPalette.HighlightedText, QColor("black"))
    app.setPalette(palette)
    # Создание и отображение главного окна
    window = MainWindow()
    # Попытка загрузки иконки
    try:
        icon_path = resource_path("../assets/app.ico")
        window.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        print(f"Не удалось загрузить иконку: {e}")
        logging.warning(f"Не удалось загрузить иконку: {e}")
    window.show()
    data = time.time() - time_s
    logging.info(f"Время запуска программы: {data:.2f} сек.")
    sys.exit(app.exec_())

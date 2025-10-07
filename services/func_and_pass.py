import getpass
import logging
import os
import subprocess
import sys
import keyring
import pyodbc


logger_ui = logging.getLogger(__name__)

# Логины
login = getpass.getuser()
password = keyring.get_password("Jira", login)
passA = keyring.get_password("AdapterA", "admin")
passP = keyring.get_password("AdapterP", "admin")
passElastic = keyring.get_password("Elastic", login)

# Путь к цитриксу
citrix_shrt = r"C:\Program Files (x86)\Citrix\ICA Client\SelfServicePlugin\SelfService.exe"
shrt = r"\PC"  # Путь
brow_shrt = fr"\\Интернет III\Интернет Internet Explorer.lnk"  # Путь к цитрикс браузеру


def resource_path(relative_path: str) -> str:
    """Получить путь к ресурсу: рядом с exe → _MEIPASS → dev"""
    # убираем ведущие / или \
    relative_path = relative_path.lstrip("/\\")
    if getattr(sys, "frozen", False):  # если это .exe
        base_path = os.path.dirname(sys.executable)
        candidate = os.path.join(base_path, relative_path)
        if os.path.exists(candidate):
            return candidate
    if hasattr(sys, "_MEIPASS"):
        candidate = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(os.path.abspath("."), relative_path)

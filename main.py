from interfaces.ui import run_interface
from services.logger import setup_logging
# Настройка логов до всех импортов
setup_logging()
if __name__ == "__main__":
    run_interface()

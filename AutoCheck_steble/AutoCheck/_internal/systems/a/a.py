import logging
from services.logger import log, init_logging


# Упрощенный интерфейс логирования
logger_ui = logging.getLogger(__name__)


def monitoring():
    try:
        print('test1')
        logger_ui.info('Успешно выполнено')
        log('Успешно выполнено', 'success')
        return  True
    except Exception as e:
        logger_ui.info(f'Ошибка - {e}')
        log('Ошибка', 'error')
        return False


def usersOnline():
    try:
        print('test1')
        logger_ui.info('Успешно выполнено')
        log('Успешно выполнено', 'success')
        return  True
    except Exception as e:
        logger_ui.info(f'Ошибка - {e}')
        log('Ошибка', 'error')
        return False


def adapterCheck():
    try:
        print('test1')
        logger_ui.info('Успешно выполнено')
        log('Успешно выполнено', 'success')
        return  True
    except Exception as e:
        logger_ui.info(f'Ошибка - {e}')
        log('Ошибка', 'error')
        return False


def check_errors_in_log_adapter():
    try:
        print('test1')
        logger_ui.info('Успешно выполнено')
        log('Успешно выполнено', 'success')
        return  True
    except Exception as e:
        logger_ui.info(f'Ошибка - {e}')
        log('Ошибка', 'error')
        return False

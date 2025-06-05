import time
import logging
from functools import wraps
import requests

logger = logging.getLogger(__name__)

def retry_on_exception(max_retries=3, retry_delay=1, backoff_factor=2, 
                      exceptions=(requests.exceptions.RequestException,)):
    """
    Декоратор для повторных попыток выполнения функции при возникновении исключений
    
    Args:
        max_retries (int): Максимальное количество повторных попыток
        retry_delay (int): Начальная задержка между попытками в секундах
        backoff_factor (int): Множитель задержки для экспоненциального отступа
        exceptions (tuple): Кортеж исключений, при которых выполнять повторные попытки
        
    Returns:
        Результат выполнения декорируемой функции
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = retry_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Превышено максимальное количество попыток ({max_retries}) "
                                     f"для функции {func.__name__}. Последняя ошибка: {str(e)}")
                        raise
                    
                    logger.warning(f"Попытка {retries}/{max_retries} для функции {func.__name__} "
                                 f"завершилась с ошибкой: {str(e)}. Повтор через {current_delay} сек.")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
        return wrapper
    return decorator

def safe_api_call(func, default_return=None, *args, **kwargs):
    """
    Безопасный вызов API-функции с возвратом значения по умолчанию при ошибке
    
    Args:
        func: Функция для вызова
        default_return: Значение, возвращаемое при ошибке
        args, kwargs: Аргументы для передачи в функцию
        
    Returns:
        Результат выполнения функции или default_return при ошибке
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка при вызове {func.__name__}: {str(e)}")
        return default_return
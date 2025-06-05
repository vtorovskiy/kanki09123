import time
import functools
import logging
from monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)

def track_api_call(api_name):
    """
    Декоратор для отслеживания вызовов API
    
    Args:
        api_name (str): Название API
        
    Returns:
        Декоратор для функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error = False
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = True
                raise
            finally:
                response_time = time.time() - start_time
                metrics_collector.track_api_call(api_name, response_time, error)
        return wrapper
    return decorator

def track_command(command_name):
    """
    Декоратор для отслеживания выполнения команд бота
    
    Args:
        command_name (str): Название команды
        
    Returns:
        Декоратор для функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(message, *args, **kwargs):
            metrics_collector.track_command(command_name)
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

def track_user_action(action_type):
    """
    Декоратор для отслеживания действий пользователя
    
    Args:
        action_type (str): Тип действия ('photo_analysis', 'barcode_scan', etc.)
        
    Returns:
        Декоратор для функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            
            if action_type == 'photo_analysis':
                metrics_collector.track_photo_analysis(user_id)
            elif action_type == 'barcode_scan':
                metrics_collector.track_barcode_scan(user_id)
            
            return func(message, *args, **kwargs)
        return wrapper
    return decorator
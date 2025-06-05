import os
import tempfile
import requests
from datetime import datetime
import sys
from database.db_manager import DatabaseManager

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def download_photo(file_path):
    """
    Загрузка фотографии по URL
    
    Args:
        file_path (str): URL фотографии
        
    Returns:
        str: Путь к временному файлу с фотографией
    """
    try:
        response = requests.get(file_path, stream=True)
        if response.status_code == 200:
            # Создаем временный файл
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            for chunk in response.iter_content(1024):
                temp_file.write(chunk)
            temp_file.close()
            return temp_file.name
        else:
            print(f"Ошибка при загрузке фотографии: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при загрузке фотографии: {str(e)}")
        return None

def format_nutrition_result(nutrition_data, user_id=None):
    """
    Форматирование результатов анализа пищевой ценности в компактном виде
    
    Args:
        nutrition_data (dict): Данные о пищевой ценности
        user_id (int, optional): Telegram ID пользователя для получения дневных норм
        
    Returns:
        str: Отформатированный текст с результатами
    """
    if not nutrition_data:
        return "Не удалось определить пищевую ценность продукта."
    
    # Получаем информацию о блюде
    dish_name = nutrition_data['name']
    portion_weight = nutrition_data.get('portion_weight', 0)
    calories = nutrition_data.get('calories', 0)
    proteins = nutrition_data.get('proteins', 0)
    fats = nutrition_data.get('fats', 0)
    carbs = nutrition_data.get('carbs', 0)
    
    # Формируем название и вес
    if portion_weight > 0:
        text = f"🍽️ *{dish_name}* ({portion_weight} г)\n"
    else:
        text = f"🍽️ *{dish_name}*\n"
    
    # Калории
    text += f"▫️Калории: *{calories}* ккал\n"
    
    # Б/Ж/У одной строкой
    text += f"▫️Б/Ж/У: *{proteins}*г | *{fats}*г | *{carbs}*г\n"
    
    # Добавляем ингредиенты, если они есть
    detected_items = nutrition_data.get('detected_items', [])
    if detected_items:
        text += f"▫️Состав: {', '.join(detected_items)}\n"
    
    return text

def get_subscription_info(remaining_requests, is_subscribed):
    """
    Формирование информации о подписке
    
    Args:
        remaining_requests (int): Количество оставшихся бесплатных запросов
        is_subscribed (bool): Статус подписки
        
    Returns:
        str: Информация о подписке
    """
    if is_subscribed:
        return "✅ У вас активная подписка. Вы можете делать неограниченное количество запросов."
    else:
        if remaining_requests > 0:
            return f"ℹ️ Для неограниченного доступа оформите подписку."
        else:
            return "❗ У вас закончились бесплатные запросы. Для продолжения работы оформите подписку."

def format_datetime(dt):
    """
    Форматирование даты и времени
    
    Args:
        dt (datetime): Дата и время
        
    Returns:
        str: Отформатированная дата и время
    """
    if not dt:
        return "Не указано"
    
    return dt.strftime("%d.%m.%Y %H:%M")


def get_remaining_subscription_days(end_date):
    """
    ИСПРАВЛЕННЫЙ расчет оставшихся дней подписки
    """
    if not end_date:
        return 0

    # Московское время (UTC+3)
    now_msk = datetime.utcnow() + timedelta(hours=3)

    # Если подписка уже истекла
    if end_date <= now_msk:
        return 0

    # Считаем разницу
    delta = end_date - now_msk

    # Возвращаем количество полных дней
    return max(0, delta.days)

def generate_progress_bar(current, target, length=10):
    """
    Генерирует текстовый прогресс-бар
    
    Args:
        current (float): Текущее значение
        target (float): Целевое значение (100%)
        length (int): Длина прогресс-бара в символах
        
    Returns:
        str: Текстовый прогресс-бар
    """
    if target <= 0:
        percent = 0
    else:
        percent = min(1.0, current / target)
    
    filled_length = int(length * percent)
    empty_length = length - filled_length
    
    bar = '■' * filled_length + '□' * empty_length
    percent_text = f"{int(percent * 100)}%"
    
    return f"{bar} {percent_text}"

def get_indicator_emoji(percent):
    """
    Возвращает эмодзи-индикатор в зависимости от процента
    
    Args:
        percent (float): Процент от нормы (0-1)
        
    Returns:
        str: Эмодзи-индикатор
    """
    if percent < 0.25:
        return "🔴"  # Очень мало
    elif percent < 0.5:
        return "🟠"  # Мало
    elif percent < 0.75:
        return "🟡"  # Средне
    elif percent < 1.0:
        return "🟢"  # Хорошо
    else:
        return "🔵"  # Достигнуто или превышено

def get_nutrition_indicators(nutrition_values, daily_norms):
    """
    Генерирует индикаторы для основных нутриентов
    
    Args:
        nutrition_values (dict): Текущие значения КБЖУ
        daily_norms (dict): Дневные нормы КБЖУ
        
    Returns:
        dict: Индикаторы для каждого нутриента
    """
    if not daily_norms:
        return None
    
    result = {}
    
    # Калории
    if daily_norms.get('daily_calories'):
        calories_percent = nutrition_values.get('calories', 0) / daily_norms['daily_calories']
        result['calories'] = {
            'percent': calories_percent,
            'bar': generate_progress_bar(nutrition_values.get('calories', 0), daily_norms['daily_calories']),
            'indicator': get_indicator_emoji(calories_percent)
        }
    
    # Белки
    if daily_norms.get('daily_proteins'):
        proteins_percent = nutrition_values.get('proteins', 0) / daily_norms['daily_proteins']
        result['proteins'] = {
            'percent': proteins_percent,
            'bar': generate_progress_bar(nutrition_values.get('proteins', 0), daily_norms['daily_proteins']),
            'indicator': get_indicator_emoji(proteins_percent)
        }
    
    # Жиры
    if daily_norms.get('daily_fats'):
        fats_percent = nutrition_values.get('fats', 0) / daily_norms['daily_fats']
        result['fats'] = {
            'percent': fats_percent,
            'bar': generate_progress_bar(nutrition_values.get('fats', 0), daily_norms['daily_fats']),
            'indicator': get_indicator_emoji(fats_percent)
        }
    
    # Углеводы
    if daily_norms.get('daily_carbs'):
        carbs_percent = nutrition_values.get('carbs', 0) / daily_norms['daily_carbs']
        result['carbs'] = {
            'percent': carbs_percent,
            'bar': generate_progress_bar(nutrition_values.get('carbs', 0), daily_norms['daily_carbs']),
            'indicator': get_indicator_emoji(carbs_percent)
        }
    
    return result
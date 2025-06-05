from google.cloud import vision
import io
import os
import sys
import requests
import json
from monitoring.decorators import track_api_call
from monitoring.decorators import track_command, track_user_action
from monitoring.metrics import metrics_collector

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GOOGLE_APPLICATION_CREDENTIALS

# Установка переменных окружения для Google Cloud API
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

class FoodRecognition:
    """Класс для распознавания пищи с использованием Google Cloud Vision API"""
    
    def __init__(self):
        self.client = vision.ImageAnnotatorClient()

    @track_api_call('google_vision')
    def detect_food(self, image_path=None, image_content=None):
        """
        Улучшенное распознавание пищи на изображении с использованием 
        нескольких методов Vision API
        
        Args:
            image_path (str, optional): Путь к файлу изображения
            image_content (bytes, optional): Содержимое изображения в байтах
            
        Returns:
            list: Список обнаруженных продуктов питания с вероятностями
        """
        try:
            # Подготовка изображения
            if image_path and os.path.exists(image_path):
                with io.open(image_path, 'rb') as image_file:
                    content = image_file.read()
            elif image_content:
                content = image_content
            else:
                raise ValueError("Необходимо предоставить либо путь к изображению, либо его содержимое")
            
            image = vision.Image(content=content)
            
            # Получаем результаты из нескольких методов API для более точного распознавания
            
            # 1. Распознавание объектов - хорошо определяет общие категории
            object_response = self.client.object_localization(image=image)
            objects = object_response.localized_object_annotations
            
            # 2. Распознавание меток - дает более детальные категории
            label_response = self.client.label_detection(image=image, max_results=15)
            labels = label_response.label_annotations
            
            # 3. Распознавание веб-сущностей - помогает найти конкретные блюда
            web_response = self.client.web_detection(image=image)
            web_entities = web_response.web_detection.web_entities
            
            # Словарь продуктов для удаления дубликатов (ключ - название, значение - уверенность)
            food_dict = {}
            
            # Фильтр слов, связанных с едой (расширенный список)
            food_keywords = [
                'food', 'meal', 'dish', 'cuisine', 'breakfast', 'lunch', 'dinner',
                'snack', 'fruit', 'vegetable', 'meat', 'fish', 'салат', 'salad',
                'pasta', 'rice', 'potato', 'bread', 'dessert', 'cake', 'soup',
                'еда', 'блюдо', 'питание', 'завтрак', 'обед', 'ужин', 'фрукт', 
                'овощ', 'мясо', 'рыба', 'салат', 'паста', 'рис', 'картофель',
                'хлеб', 'десерт', 'торт', 'суп', 'pizza', 'burger', 'sandwich',
                'steak', 'chicken', 'beef', 'pork', 'seafood', 'sushi', 'noodle',
                'пицца', 'бургер', 'сэндвич', 'стейк', 'курица', 'говядина', 'свинина',
                'морепродукты', 'суши', 'лапша', 'карбонара', 'борщ', 'плов', 'котлета',
                'пельмени', 'вареники', 'роллы', 'паэлья', 'лазанья', 'равиоли',
                'carbonara', 'borsch', 'pilaf', 'cutlet', 'dumplings', 'rolls', 
                'paella', 'lasagna', 'ravioli', 'apple', 'banana', 'orange', 'grape',
                'яблоко', 'банан', 'апельсин', 'виноград', 'молоко', 'milk', 'cheese', 'сыр'
            ]
            
            # Обработка результатов локализации объектов
            for obj in objects:
                if any(keyword.lower() in obj.name.lower() for keyword in food_keywords) or obj.score > 0.7:
                    # Если объект связан с едой или имеет высокую уверенность
                    food_dict[obj.name] = max(food_dict.get(obj.name, 0), obj.score)
            
            # Обработка результатов распознавания меток
            for label in labels:
                if any(keyword.lower() in label.description.lower() for keyword in food_keywords) or label.score > 0.7:
                    # Если метка связана с едой или имеет высокую уверенность
                    food_dict[label.description] = max(food_dict.get(label.description, 0), label.score)
            
            # Обработка веб-сущностей для получения конкретных названий блюд
            for entity in web_entities:
                if entity.score > 0.5 and any(keyword.lower() in entity.description.lower() for keyword in food_keywords):
                    # Если веб-сущность связана с едой и имеет достаточную уверенность
                    food_dict[entity.description] = max(food_dict.get(entity.description, 0), entity.score)
            
            # Преобразование словаря в список и сортировка по уверенности
            food_items = [{'name': name, 'confidence': score} for name, score in food_dict.items()]
            food_items.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Если распознано слишком много элементов, оставляем только наиболее вероятные
            if len(food_items) > 10:
                food_items = food_items[:10]
            
            # Проверка на ошибки
            if label_response.error.message:
                raise Exception(f"Ошибка при распознавании изображения: {label_response.error.message}")
                
            return food_items
        
        except Exception as e:
            print(f"Ошибка в FoodRecognition.detect_food: {str(e)}")
            return None
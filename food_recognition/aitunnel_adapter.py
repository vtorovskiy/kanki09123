import sys
import os
from typing import Dict, Any, List, Optional


# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from food_recognition.aitunnel_vision_api import AITunnelVisionFoodRecognition
from food_recognition.nutrition_calc import NutritionCalculator

class AITunnelNutritionAdapter:
    """
    Адаптер для обработки данных от AITunnel Vision API и преобразования их
    в формат, совместимый с существующим кодом
    """
    
    def __init__(self):
        self.aitunnel_vision = AITunnelVisionFoodRecognition()
    
    def process_image(self, image_path: Optional[str] = None, image_content: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Обработка изображения для распознавания пищи или штрихкода
        
        Args:
            image_path (str, optional): Путь к файлу изображения
            image_content (bytes, optional): Содержимое изображения в байтах
                
        Returns:
            dict: Данные о пищевой ценности в стандартном формате
        """
        food_items = self.aitunnel_vision.detect_food(image_path, image_content)
        
        if not food_items:
            # Если AITunnel Vision не смог распознать еду, пробуем резервный метод
            return self._fallback_nutrition_calculation(image_path, image_content)
        
        # Берем первый (и обычно единственный) элемент из результатов
        food_item = food_items[0]
        
        # Проверка на отсутствие еды на изображении
        if 'no_food' in food_item and food_item['no_food'] or food_item['name'] == "Еда не обнаружена":
            return {
                'name': 'Еда не обнаружена',
                'no_food': True,
                'calories': 0,
                'proteins': 0, 
                'fats': 0,
                'carbs': 0
            }
        
        # Проверяем, вернул ли GPT-4 данные о питательной ценности
        if 'nutrition' in food_item and food_item['nutrition']:
            nutrition = food_item['nutrition']
            
            # Формируем результат в стандартном формате с добавлением веса порции
            result = {
                'name': food_item['name'],
                'calories': nutrition.get('calories', 0),
                'proteins': nutrition.get('proteins', 0),
                'fats': nutrition.get('fats', 0),
                'carbs': nutrition.get('carbs', 0),
                'estimated': False,  # GPT-4 обычно дает точные данные
                'detected_items': food_item.get('ingredients', []),
                'portion_weight': food_item.get('portion_weight', 0)  # Добавляем вес порции
            }
            
            return result
        else:
            # Если в ответе нет данных о КБЖУ, используем наш калькулятор
            return self._calculate_nutrition_from_name(food_item['name'])
    
    def _fallback_nutrition_calculation(self, image_path: Optional[str], image_content: Optional[bytes]) -> Dict[str, Any]:
        """
        Резервный метод расчета питательной ценности с использованием существующего кода
        
        Args:
            image_path (str, optional): Путь к файлу изображения
            image_content (bytes, optional): Содержимое изображения в байтах
            
        Returns:
            dict: Данные о пищевой ценности
        """
        # Здесь можно использовать ваш существующий код для распознавания пищи
        # Например, через Google Vision API
        from food_recognition.vision_api import FoodRecognition
        
        vision_api = FoodRecognition()
        food_items = vision_api.detect_food(image_path, image_content)
        
        if not food_items:
            return {
                'name': 'Неизвестное блюдо',
                'calories': 0,
                'proteins': 0,
                'fats': 0,
                'carbs': 0,
                'estimated': True
            }
        
        # Используем существующий калькулятор КБЖУ
        return NutritionCalculator.calculate_nutrition(food_items)
    
    def _calculate_nutrition_from_name(self, food_name: str) -> Dict[str, Any]:
        """
        Расчет питательной ценности по названию блюда
        
        Args:
            food_name (str): Название блюда
            
        Returns:
            dict: Данные о пищевой ценности
        """
        # Используем существующий калькулятор КБЖУ
        nutrition = NutritionCalculator.lookup_nutrition(food_name)
        
        # Добавляем detected_items для совместимости
        if 'detected_items' not in nutrition:
            nutrition['detected_items'] = [food_name]
        
        return nutrition

    def process_voice(self, voice_file_path: str) -> Dict[str, Any]:
        """
        Обработка голосового сообщения

        Args:
            voice_file_path (str): Путь к аудиофайлу

        Returns:
            dict: Данные о пищевой ценности
        """
        # Сначала распознаем голос в текст
        text = self.aitunnel_vision.transcribe_voice(voice_file_path)

        if not text:
            return {
                'name': 'Не удалось распознать голос',
                'no_voice': True,
                'calories': 0,
                'proteins': 0,
                'fats': 0,
                'carbs': 0
            }

        # Затем анализируем текст
        return self.process_text(text)

    def process_text(self, food_description: str) -> Dict[str, Any]:
        """
        Обработка текстового описания еды

        Args:
            food_description (str): Описание блюда

        Returns:
            dict: Данные о пищевой ценности
        """
        food_items = self.aitunnel_vision.analyze_food_from_text(food_description)

        if not food_items:
            return {
                'name': 'Не удалось проанализировать',
                'calories': 0,
                'proteins': 0,
                'fats': 0,
                'carbs': 0,
                'estimated': True
            }

        food_item = food_items[0]

        # Проверка на отсутствие еды
        if 'no_food' in food_item and food_item['no_food'] or food_item['name'] == "Это не еда":
            return {
                'name': 'Это не еда',
                'no_food': True,
                'calories': 0,
                'proteins': 0,
                'fats': 0,
                'carbs': 0
            }

        # Формируем результат
        if 'nutrition' in food_item and food_item['nutrition']:
            nutrition = food_item['nutrition']

            result = {
                'name': food_item['name'],
                'calories': nutrition.get('calories', 0),
                'proteins': nutrition.get('proteins', 0),
                'fats': nutrition.get('fats', 0),
                'carbs': nutrition.get('carbs', 0),
                'estimated': False,
                'detected_items': food_item.get('ingredients', []),
                'portion_weight': food_item.get('portion_weight', 100)
            }

            return result
        else:
            return self._calculate_nutrition_from_name(food_item['name'])
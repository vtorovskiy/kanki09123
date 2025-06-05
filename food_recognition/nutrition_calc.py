import requests
import json
import os
import sys
import re

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class NutritionCalculator:
    """Класс для расчета КБЖУ на основе распознанных продуктов питания"""
    
    # Расширенная база данных с пищевой ценностью продуктов и блюд
    # Формат: 'продукт': [калории, белки, жиры, углеводы] на 100г
    NUTRITION_DB = {
        # Фрукты
        'apple': [52, 0.3, 0.2, 14],
        'яблоко': [52, 0.3, 0.2, 14],
        'banana': [96, 1.2, 0.2, 22],
        'банан': [96, 1.2, 0.2, 22],
        'orange': [47, 0.9, 0.1, 12],
        'апельсин': [47, 0.9, 0.1, 12],
        'strawberry': [33, 0.7, 0.3, 7.7],
        'клубника': [33, 0.7, 0.3, 7.7],
        'grape': [69, 0.6, 0.2, 18],
        'виноград': [69, 0.6, 0.2, 18],
        'pineapple': [50, 0.5, 0.1, 13],
        'ананас': [50, 0.5, 0.1, 13],
        'watermelon': [30, 0.6, 0.2, 7.6],
        'арбуз': [30, 0.6, 0.2, 7.6],
        'peach': [39, 0.9, 0.3, 9.5],
        'персик': [39, 0.9, 0.3, 9.5],
        'mango': [60, 0.8, 0.4, 15],
        'манго': [60, 0.8, 0.4, 15],
        
        # Овощи
        'potato': [77, 2, 0.1, 17],
        'картофель': [77, 2, 0.1, 17],
        'tomato': [18, 0.9, 0.2, 3.9],
        'помидор': [18, 0.9, 0.2, 3.9],
        'cucumber': [15, 0.7, 0.1, 3.6],
        'огурец': [15, 0.7, 0.1, 3.6],
        'carrot': [41, 0.9, 0.2, 9.6],
        'морковь': [41, 0.9, 0.2, 9.6],
        'onion': [40, 1.1, 0.1, 9.3],
        'лук': [40, 1.1, 0.1, 9.3],
        'cabbage': [25, 1.3, 0.2, 5.8],
        'капуста': [25, 1.3, 0.2, 5.8],
        'broccoli': [34, 2.8, 0.4, 6.6],
        'брокколи': [34, 2.8, 0.4, 6.6],
        'bell pepper': [31, 1, 0.3, 6],
        'болгарский перец': [31, 1, 0.3, 6],
        
        # Мясо и птица
        'chicken': [165, 31, 3.6, 0],
        'курица': [165, 31, 3.6, 0],
        'beef': [250, 26, 17, 0],
        'говядина': [250, 26, 17, 0],
        'pork': [242, 27, 14, 0],
        'свинина': [242, 27, 14, 0],
        'turkey': [135, 29, 2.0, 0],
        'индейка': [135, 29, 2.0, 0],
        'lamb': [294, 25, 21, 0],
        'баранина': [294, 25, 21, 0],
        'veal': [172, 26, 7.5, 0],
        'телятина': [172, 26, 7.5, 0],
        
        # Рыба и морепродукты
        'fish': [206, 22, 12, 0],
        'рыба': [206, 22, 12, 0],
        'salmon': [208, 20, 13, 0],
        'лосось': [208, 20, 13, 0],
        'tuna': [184, 30, 6, 0],
        'тунец': [184, 30, 6, 0],
        'cod': [82, 17.8, 0.7, 0],
        'треска': [82, 17.8, 0.7, 0],
        'shrimp': [99, 24, 0.3, 0.2],
        'креветки': [99, 24, 0.3, 0.2],
        'crab': [83, 18, 1, 0],
        'краб': [83, 18, 1, 0],
        
        # Молочные продукты
        'milk': [42, 3.4, 1, 5],
        'молоко': [42, 3.4, 1, 5],
        'cheese': [402, 25, 33, 1.3],
        'сыр': [402, 25, 33, 1.3],
        'yogurt': [59, 3.6, 3.3, 4.7],
        'йогурт': [59, 3.6, 3.3, 4.7],
        'cottage cheese': [98, 11, 4.3, 3.4],
        'творог': [98, 11, 4.3, 3.4],
        'butter': [717, 0.9, 81, 0.1],
        'масло': [717, 0.9, 81, 0.1],
        
        # Злаки и крупы
        'rice': [130, 2.7, 0.3, 28],
        'рис': [130, 2.7, 0.3, 28],
        'pasta': [131, 5, 1.1, 25],
        'макароны': [131, 5, 1.1, 25],
        'bread': [265, 9, 3.2, 49],
        'хлеб': [265, 9, 3.2, 49],
        'oatmeal': [68, 2.5, 1.4, 12],
        'овсянка': [68, 2.5, 1.4, 12],
        'buckwheat': [343, 13.3, 3.4, 68],
        'гречка': [343, 13.3, 3.4, 68],
        'quinoa': [120, 4.4, 1.9, 21],
        'киноа': [120, 4.4, 1.9, 21],
        
        # Орехи и семечки
        'nuts': [607, 20, 54, 19],
        'орехи': [607, 20, 54, 19],
        'almonds': [576, 21, 49, 22],
        'миндаль': [576, 21, 49, 22],
        'walnuts': [654, 15, 65, 14],
        'грецкие орехи': [654, 15, 65, 14],
        'peanuts': [567, 26, 49, 16],
        'арахис': [567, 26, 49, 16],
        'sunflower seeds': [584, 21, 51, 20],
        'семечки подсолнуха': [584, 21, 51, 20],
        
        # Бобовые
        'beans': [127, 8.7, 0.5, 23],
        'фасоль': [127, 8.7, 0.5, 23],
        'lentils': [116, 9, 0.4, 20],
        'чечевица': [116, 9, 0.4, 20],
        'chickpeas': [364, 19, 6, 61],
        'нут': [364, 19, 6, 61],
        
        # Яйца
        'egg': [155, 13, 11, 1.1],
        'яйцо': [155, 13, 11, 1.1],
        
        # Сладости и десерты
        'chocolate': [546, 4.9, 31, 61],
        'шоколад': [546, 4.9, 31, 61],
        'cake': [257, 4, 14, 27.5],
        'торт': [257, 4, 14, 27.5],
        'ice cream': [207, 3.5, 11, 23],
        'мороженое': [207, 3.5, 11, 23],
        'cookie': [480, 5, 24, 64],
        'печенье': [480, 5, 24, 64],
        
        # Готовые блюда
        'pizza': [266, 11, 10, 33],
        'пицца': [266, 11, 10, 33],
        'burger': [295, 17, 14, 24],
        'бургер': [295, 17, 14, 24],
        'fries': [312, 3.4, 15, 41],
        'картошка фри': [312, 3.4, 15, 41],
        'soup': [75, 4, 2.5, 9],
        'суп': [75, 4, 2.5, 9],
        'sushi': [145, 5.8, 0.3, 30],
        'суши': [145, 5.8, 0.3, 30],
        'salad': [15, 1.5, 0.2, 2.9],
        'салат': [15, 1.5, 0.2, 2.9],
        'sandwich': [248, 11, 8, 35],
        'сэндвич': [248, 11, 8, 35],
        'pasta carbonara': [380, 10.6, 23.3, 32.7],
        'паста карбонара': [380, 10.6, 23.3, 32.7],
        'pilaf': [165, 3.5, 4.7, 27.3],
        'плов': [165, 3.5, 4.7, 27.3],
        'borsch': [49, 1.8, 2.4, 5.9],
        'борщ': [49, 1.8, 2.4, 5.9],
        
        # Напитки
        'coffee': [2, 0.1, 0, 0],
        'кофе': [2, 0.1, 0, 0],
        'tea': [1, 0, 0, 0.3],
        'чай': [1, 0, 0, 0.3],
        'soda': [42, 0, 0, 10.6],
        'газировка': [42, 0, 0, 10.6],
        'juice': [46, 0.5, 0.1, 11],
        'сок': [46, 0.5, 0.1, 11],
        
        # Фастфуд и снеки
        'hot dog': [242, 10, 15, 18],
        'хот-дог': [242, 10, 15, 18],
        'chips': [536, 7, 35, 53],
        'чипсы': [536, 7, 35, 53],
        'popcorn': [375, 11, 4.2, 78],
        'попкорн': [375, 11, 4.2, 78],
        'nachos': [346, 8, 18, 41],
        'начос': [346, 8, 18, 41],
    }
    
    # Словарь блюд и их компонентов для более точного определения
    DISH_COMPONENTS = {
        'pizza': ['dough', 'cheese', 'tomato sauce'],
        'пицца': ['тесто', 'сыр', 'томатный соус'],
        'burger': ['bun', 'beef patty', 'cheese', 'lettuce'],
        'бургер': ['булочка', 'котлета', 'сыр', 'салат'],
        'sushi': ['rice', 'fish', 'seaweed'],
        'суши': ['рис', 'рыба', 'водоросли'],
        'pasta carbonara': ['pasta', 'eggs', 'bacon', 'cheese'],
        'паста карбонара': ['макароны', 'яйца', 'бекон', 'сыр'],
        'salad': ['lettuce', 'tomato', 'cucumber', 'oil'],
        'салат': ['листья салата', 'помидор', 'огурец', 'масло'],
    }
    
    # Синонимы для продуктов (чтобы учитывать разные названия одного продукта)
    FOOD_SYNONYMS = {
        'beef patty': 'beef',
        'говяжья котлета': 'говядина',
        'french fries': 'fries',
        'картофель фри': 'картошка фри',
        'yoghurt': 'yogurt',
        'йогурт': 'йогурт',
        'tomatoes': 'tomato',
        'помидоры': 'помидор',
        'cucumbers': 'cucumber',
        'огурцы': 'огурец',
        'apples': 'apple',
        'яблоки': 'яблоко',
    }
    
    @staticmethod
    def normalize_food_name(food_name):
        """
        Нормализация названия продукта (приведение к стандартному виду)
        
        Args:
            food_name (str): Исходное название продукта
            
        Returns:
            str: Нормализованное название продукта
        """
        food_name_lower = food_name.lower()
        
        # Проверка синонимов
        for synonym, standard in NutritionCalculator.FOOD_SYNONYMS.items():
            if synonym.lower() in food_name_lower:
                return standard
        
        # Удаление стоп-слов и лишних символов
        food_name_clean = re.sub(r'[^\w\s]', '', food_name_lower)
        food_name_clean = food_name_clean.strip()
        
        return food_name_clean
    
    @staticmethod
    def lookup_nutrition(food_name):
        """
        Поиск пищевой ценности продукта в базе данных
        
        Args:
            food_name (str): Название продукта
            
        Returns:
            dict: Информация о пищевой ценности продукта
        """
        # Нормализация названия продукта
        food_name_norm = NutritionCalculator.normalize_food_name(food_name)
        
        # Поиск по полному совпадению
        if food_name_norm in NutritionCalculator.NUTRITION_DB:
            values = NutritionCalculator.NUTRITION_DB[food_name_norm]
            return {
                'name': food_name,
                'calories': values[0],
                'proteins': values[1],
                'fats': values[2],
                'carbs': values[3]
            }
        
        # Поиск по частичному совпадению
        for key in NutritionCalculator.NUTRITION_DB:
            if key in food_name_norm or food_name_norm in key:
                values = NutritionCalculator.NUTRITION_DB[key]
                return {
                    'name': food_name,
                    'calories': values[0],
                    'proteins': values[1],
                    'fats': values[2],
                    'carbs': values[3]
                }
        
        # Проверка компонентов блюда
        for dish, components in NutritionCalculator.DISH_COMPONENTS.items():
            if dish in food_name_norm or food_name_norm in dish:
                if dish in NutritionCalculator.NUTRITION_DB:
                    values = NutritionCalculator.NUTRITION_DB[dish]
                    return {
                        'name': food_name,
                        'calories': values[0],
                        'proteins': values[1],
                        'fats': values[2],
                        'carbs': values[3]
                    }
        
        # Если продукт не найден, возвращаем оценочные значения
        # Среднее значение КБЖУ для смешанного блюда
        return {
            'name': food_name,
            'calories': 200,
            'proteins': 10,
            'fats': 7,
            'carbs': 20,
            'estimated': True  # Флаг, что значения оценочные
        }
    
    @staticmethod
    def calculate_nutrition(food_items):
        """
        Расчет пищевой ценности для списка продуктов
        
        Args:
            food_items (list): Список распознанных продуктов с вероятностями
            
        Returns:
            dict: Информация о пищевой ценности блюда
        """
        if not food_items:
            return {
                'name': 'Неизвестное блюдо',
                'calories': 0,
                'proteins': 0,
                'fats': 0,
                'carbs': 0,
                'estimated': True
            }
        
        # Сортировка по уверенности (от высокой к низкой)
        food_items.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Определяем основное блюдо (с наивысшей вероятностью)
        main_food = food_items[0]['name']
        
        # Проверяем, есть ли это блюдо в базе данных
        main_food_nutrition = NutritionCalculator.lookup_nutrition(main_food)
        
        # Если это известное блюдо (не оценочное), возвращаем его значения
        if not main_food_nutrition.get('estimated', False):
            return main_food_nutrition
        
        # Если блюдо не найдено в базе, используем компонентный подход
        
        # Берем топ-3 продукта для расчета
        top_foods = food_items[:3]
        
        total_calories = 0
        total_proteins = 0
        total_fats = 0
        total_carbs = 0
        estimated = False
        
        # Взвешенный расчет пищевой ценности на основе вероятностей
        total_confidence = sum(item.get('confidence', 0) for item in top_foods)
        
        if total_confidence == 0:
            total_confidence = 1  # Избегаем деления на ноль
            
        for item in top_foods:
            food_name = item['name']
            confidence = item.get('confidence', 0.33)  # По умолчанию равное распределение
            
            # Нормализация уверенности
            weight = confidence / total_confidence
            
            # Получение пищевой ценности
            nutrition = NutritionCalculator.lookup_nutrition(food_name)
            
            # Учет оценочных значений
            if nutrition.get('estimated', False):
                estimated = True
            
            # Взвешенное суммирование
            total_calories += nutrition['calories'] * weight
            total_proteins += nutrition['proteins'] * weight
            total_fats += nutrition['fats'] * weight
            total_carbs += nutrition['carbs'] * weight
        
        return {
            'name': main_food,
            'calories': round(total_calories, 1),
            'proteins': round(total_proteins, 1),
            'fats': round(total_fats, 1),
            'carbs': round(total_carbs, 1),
            'estimated': estimated,
            'detected_items': [item['name'] for item in top_foods]  # Добавляем список распознанных продуктов
        }
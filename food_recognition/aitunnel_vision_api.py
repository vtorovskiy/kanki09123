import os
import sys
import base64
import requests
import json
import re
from openai import OpenAI
from typing import Optional, List, Dict, Any
from utils.api_helpers import retry_on_exception
from monitoring.decorators import track_command, track_user_action, track_api_call
from monitoring.metrics import metrics_collector
from pydub import AudioSegment
import tempfile

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AITUNNEL_API_KEY

class AITunnelVisionFoodRecognition:
    """Класс для распознавания еды с использованием GPT-4 Vision через AITunnel API"""
    
    def __init__(self):
        self.api_key = AITUNNEL_API_KEY
        if not self.api_key:
            raise ValueError("AITUNNEL_API_KEY не задан в конфигурации")
        
        # Инициализация клиента OpenAI с базовым URL AITunnel
        self.client = OpenAI(
            api_key=self.api_key,
            base_url='https://api.aitunnel.ru/v1/'
        )
        
        # Модель GPT-4 Vision
        self.model = "gpt-4o"  # или "gpt-4-vision-preview" в зависимости от доступных моделей

    @track_api_call('aitunnel_encode_image')
    def _encode_image(self, image_path: str) -> str:
        """
        Кодирование изображения в base64 для отправки в API
        
        Args:
            image_path (str): Путь к файлу изображения
            
        Returns:
            str: Изображение, закодированное в base64
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
            
    @retry_on_exception(max_retries=3, retry_delay=2, 
                   exceptions=(requests.exceptions.RequestException, ValueError))
    @track_api_call('aitunnel_vision')
    def detect_food(self, image_path: Optional[str] = None, image_content: Optional[bytes] = None) -> List[Dict[str, Any]]:
        """
        Распознавание пищи на изображении с помощью GPT-4 Vision через AITunnel
        
        Args:
            image_path (str, optional): Путь к файлу изображения
            image_content (bytes, optional): Содержимое изображения в байтах
            
        Returns:
            list: Список обнаруженных продуктов с информацией о КБЖУ
        """
        try:
            # Подготовка изображения
            if image_path and os.path.exists(image_path):
                base64_image = self._encode_image(image_path)
            elif image_content:
                base64_image = base64.b64encode(image_content).decode('utf-8')
            else:
                raise ValueError("Необходимо предоставить либо путь к изображению, либо его содержимое")
            
            # Инструкция для модели с запросом определить еду и КБЖУ
            prompt = """
            Ты эксперт-диетолог с обширными знаниями о пищевой ценности продуктов.
            Проанализируй это изображение и определи, какая еда на нем показана.
            
            Важно:
            1. Если на изображении нет еды, укажи "Еда не обнаружена" в поле name и верни пустые значения
            2. Если еда есть, определи как можно точнее, что это за блюдо/продукт
            3. Укажи основные ингредиенты
            4. Оцени приблизительный вес всей порции в граммах
            5. Рассчитай пищевую ценность ВСЕЙ порции (не на 100г):
               - Калории (ккал)
               - Белки (г)
               - Жиры (г)
               - Углеводы (г)
            
            Верни ответ только в таком формате JSON:
            {
                "name": "Название блюда",
                "has_food": true/false,
                "ingredients": ["ингредиент1", "ингредиент2", ...],
                "portion_weight": число_в_граммах,
                "nutrition": {
                    "calories": число,
                    "proteins": число,
                    "fats": число,
                    "carbs": число
                }
            }
            """
            
            # Формирование запроса к API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url", 
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"  # Высокая детализация для лучшего распознавания
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.2  # Низкая температура для более точных и стабильных ответов
            )
            
            # Получение ответа от модели
            message_content = response.choices[0].message.content.strip()
            
            # Проверка на наличие еды в ответе модели
            if "еда не обнаружена" in message_content.lower() or "нет еды" in message_content.lower():
                return [{
                    'name': "Еда не обнаружена",
                    'confidence': 0,
                    'no_food': True  # Специальный флаг для обозначения отсутствия еды
                }]
            
            # Извлечение JSON из ответа
            json_match = re.search(r'({[\s\S]*})', message_content)
            if json_match:
                json_str = json_match.group(1)
                try:
                    food_data = json.loads(json_str)
                    
                    # Проверка на отсутствие еды в JSON
                    if 'has_food' in food_data and not food_data['has_food']:
                        return [{
                            'name': "Еда не обнаружена",
                            'confidence': 0,
                            'no_food': True  # Специальный флаг для обозначения отсутствия еды
                        }]
                    
                    # Формируем список для совместимости с существующим кодом
                    food_items = [{
                        'name': food_data.get('name', 'Неизвестное блюдо'),
                        'confidence': 0.95,  # GPT-4 обычно дает точные ответы
                        'ingredients': food_data.get('ingredients', []),
                        'nutrition': food_data.get('nutrition', {
                            'calories': 0,
                            'proteins': 0,
                            'fats': 0,
                            'carbs': 0
                        }),
                        'portion_weight': food_data.get('portion_weight', 0)
                    }]
                    
                    return food_items
                except json.JSONDecodeError:
                    # Если не удалось распарсить JSON
                    # Проверим еще раз, нет ли упоминания отсутствия еды
                    if "еда не обнаружена" in message_content.lower() or "нет еды" in message_content.lower():
                        return [{
                            'name': "Еда не обнаружена",
                            'confidence': 0,
                            'no_food': True
                        }]
                    return [{
                        'name': "Нераспознанное блюдо",
                        'confidence': 0.5,
                        'raw_response': message_content
                    }]
            else:
                # Если JSON не найден, проверим на упоминание отсутствия еды
                if "еда не обнаружена" in message_content.lower() or "нет еды" in message_content.lower():
                    return [{
                        'name': "Еда не обнаружена",
                        'confidence': 0,
                        'no_food': True
                    }]
                # Если JSON не найден
                return [{
                    'name': "Нераспознанное блюдо",
                    'confidence': 0.5,
                    'raw_response': message_content
                }]
                
        except Exception as e:
            print(f"Ошибка в AITunnelVisionFoodRecognition.detect_food: {str(e)}")
            return None

    @track_api_call('aitunnel_voice_to_text')
    def transcribe_voice(self, voice_file_path: str) -> str:
        """
        Преобразование голосового сообщения в текст с помощью Whisper API

        Args:
            voice_file_path (str): Путь к аудиофайлу

        Returns:
            str: Распознанный текст
        """
        converted_file_path = None
        try:
            # Конвертируем .oga в .wav для совместимости с Whisper
            audio = AudioSegment.from_file(voice_file_path)

            # Создаем временный файл с расширением .wav
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                converted_file_path = temp_file.name

            # Экспортируем в wav формат
            audio.export(converted_file_path, format="wav")

            # Отправляем конвертированный файл в Whisper
            with open(converted_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"  # Указываем русский язык для лучшего распознавания
                )
            return transcript.text

        except Exception as e:
            print(f"Ошибка при распознавании голоса: {str(e)}")
            return None
        finally:
            # Удаляем временный конвертированный файл
            if converted_file_path and os.path.exists(converted_file_path):
                os.remove(converted_file_path)

    @track_api_call('aitunnel_analyze_text')
    def analyze_food_from_text(self, food_description: str) -> List[Dict[str, Any]]:
        """
        Анализ текстового описания еды с помощью GPT-4

        Args:
            food_description (str): Описание блюда текстом

        Returns:
            list: Список с данными о пищевой ценности
        """
        try:
            # Инструкция для модели
            prompt = f"""
            Ты эксперт-диетолог с обширными знаниями о пищевой ценности продуктов.
            Проанализируй это описание еды: "{food_description}"

            Важно:
            1. Если описание не относится к еде, укажи "Это не еда" в поле name и верни пустые значения
            2. Если это еда, определи как можно точнее, что это за блюдо/продукт
            3. Укажи основные ингредиенты
            4. Оцени приблизительный вес стандартной порции в граммах
            5. Рассчитай пищевую ценность ВСЕЙ порции (не на 100г):
               - Калории (ккал)
               - Белки (г)
               - Жиры (г)
               - Углеводы (г)

            Верни ответ только в таком формате JSON:
            {{
                "name": "Название блюда",
                "has_food": true/false,
                "ingredients": ["ингредиент1", "ингредиент2", ...],
                "portion_weight": число_в_граммах,
                "nutrition": {{
                    "calories": число,
                    "proteins": число,
                    "fats": число,
                    "carbs": число
                }}
            }}
            """

            # Отправляем запрос к GPT-4
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )

            message_content = response.choices[0].message.content.strip()

            # Проверка на отсутствие еды
            if "это не еда" in message_content.lower():
                return [{
                    'name': "Это не еда",
                    'confidence': 0,
                    'no_food': True
                }]

            # Извлечение JSON из ответа
            json_match = re.search(r'({[\s\S]*})', message_content)
            if json_match:
                json_str = json_match.group(1)
                try:
                    food_data = json.loads(json_str)

                    # Проверка на отсутствие еды в JSON
                    if 'has_food' in food_data and not food_data['has_food']:
                        return [{
                            'name': "Это не еда",
                            'confidence': 0,
                            'no_food': True
                        }]

                    # Формируем результат
                    food_items = [{
                        'name': food_data.get('name', 'Неизвестное блюдо'),
                        'confidence': 0.95,
                        'ingredients': food_data.get('ingredients', []),
                        'nutrition': food_data.get('nutrition', {
                            'calories': 0,
                            'proteins': 0,
                            'fats': 0,
                            'carbs': 0
                        }),
                        'portion_weight': food_data.get('portion_weight', 100)
                    }]

                    return food_items
                except json.JSONDecodeError:
                    return [{
                        'name': "Нераспознанное блюдо",
                        'confidence': 0.5,
                        'raw_response': message_content
                    }]
            else:
                return [{
                    'name': "Нераспознанное блюдо",
                    'confidence': 0.5,
                    'raw_response': message_content
                }]

        except Exception as e:
            print(f"Ошибка при анализе текста: {str(e)}")
            return None
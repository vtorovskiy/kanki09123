from yookassa import Configuration, Payment
import uuid
import sys
import os
from monitoring.decorators import track_api_call
from monitoring.decorators import track_command, track_user_action
from monitoring.metrics import metrics_collector

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import YUKASSA_SHOP_ID, YUKASSA_SECRET_KEY, SUBSCRIPTION_COST, WEBHOOK_URL

# Настройка конфигурации ЮKassa
Configuration.account_id = YUKASSA_SHOP_ID
Configuration.secret_key = YUKASSA_SECRET_KEY

class YuKassaPayment:
    """Класс для работы с платежной системой ЮKassa"""
    
    @track_api_call('yukassa_create_payment')
    @staticmethod
    def create_payment(user_id, months=1, description="Подписка на бота для анализа КБЖУ"):
        """
        Создание платежа в ЮKassa
        
        Args:
            user_id (int): Telegram ID пользователя
            months (int): Количество месяцев подписки
            description (str): Описание платежа
            
        Returns:
            dict: Информация о созданном платеже
        """
        try:
            # Формирование идентификатора платежа
            idempotence_key = str(uuid.uuid4())
            
            # Расчет стоимости
            amount = SUBSCRIPTION_COST * months
            
            # Создание платежа
            payment = Payment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{WEBHOOK_URL}/payment_callback?user_id={user_id}"
                },
                "capture": True,
                "description": f"{description} на {months} мес.",
                "metadata": {
                    "user_id": user_id,
                    "months": months
                }
            }, idempotence_key)
            
            payment_data = {
                "id": payment.id,
                "status": payment.status,
                "amount": payment.amount.value,
                "currency": payment.amount.currency,
                "confirmation_url": payment.confirmation.confirmation_url if payment.confirmation else None
            }
            
            return payment_data
        
        except Exception as e:
            print(f"Ошибка при создании платежа: {str(e)}")
            return None
    
    @track_api_call('yukassa_check_payment')
    @staticmethod
    def check_payment_status(payment_id):
        """
        Проверка статуса платежа
        
        Args:
            payment_id (str): Идентификатор платежа
            
        Returns:
            dict: Информация о статусе платежа
        """
        try:
            payment = Payment.find_one(payment_id)
            
            return {
                "id": payment.id,
                "status": payment.status,
                "paid": payment.paid,
                "amount": payment.amount.value,
                "currency": payment.amount.currency,
                "metadata": payment.metadata
            }
        except Exception as e:
            print(f"Ошибка при проверке статуса платежа: {str(e)}")
            return None
    
    @track_api_call('yukassa_process_webhook')
    @staticmethod
    def process_webhook(data):
        """
        Обработка вебхука от ЮKassa
        
        Args:
            data (dict): Данные вебхука
            
        Returns:
            dict: Обработанные данные платежа или None в случае ошибки
        """
        try:
            # Проверяем тип события
            if data.get('event') != 'payment.succeeded':
                return None
                
            # Получаем информацию о платеже
            payment_data = data.get('object')
            if not payment_data:
                return None
                
            # Проверяем статус платежа
            if payment_data.get('status') != 'succeeded':
                return None
                
            # Получаем метаданные
            metadata = payment_data.get('metadata', {})
            user_id = metadata.get('user_id')
            months = metadata.get('months', 1)
            
            if not user_id:
                return None
                
            return {
                "payment_id": payment_data.get('id'),
                "user_id": int(user_id),
                "months": int(months),
                "amount": payment_data.get('amount', {}).get('value')
            }
            
        except Exception as e:
            print(f"Ошибка при обработке вебхука: {str(e)}")
            return None
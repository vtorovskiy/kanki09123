from flask import Flask, request, jsonify
import telebot
import logging
import os
import sys
from datetime import datetime
from utils.helpers import format_datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Импорт модулей проекта
from config import (
    TELEGRAM_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_HOST,
    WEBHOOK_PORT, WEBHOOK_LISTEN, WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV
)
from bot import bot
from database.db_manager import DatabaseManager
from payments.yukassa import YuKassaPayment

# Инициализация Flask-приложения
app = Flask(__name__)

# Установка вебхука для Telegram
@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Установка вебхука для Telegram"""
    bot.remove_webhook()
    url = f"{WEBHOOK_URL}/bot{TELEGRAM_BOT_TOKEN}"
    
    if WEBHOOK_SSL_CERT:
        bot.set_webhook(url=url, certificate=open(WEBHOOK_SSL_CERT, 'r'))
    else:
        bot.set_webhook(url=url)
    
    return "Webhook установлен!"

# Обработчик запросов от Telegram
@app.route(f'/bot{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    """Обработчик запросов от Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Некорректный запрос'

# Обработчик обратных вызовов от ЮKassa
@app.route('/payment_notification', methods=['POST'])
def payment_notification():
    """Обработчик обратных вызовов от ЮKassa"""
    try:
        # Получение данных от ЮKassa
        data = request.json
        
        # Обработка вебхука
        payment_data = YuKassaPayment.process_webhook(data)
        
        if payment_data:
            # Добавление подписки пользователю
            user_id = payment_data['user_id']
            months = payment_data['months']
            payment_id = payment_data['payment_id']
            
            # Добавление подписки
            subscription = DatabaseManager.add_subscription(user_id, months, payment_id)
            
            if subscription:
                # Отправка уведомления пользователю
                end_date = format_datetime(subscription.end_date)
                
                message_text = (
                    "✅ *Подписка успешно оформлена!*\n\n"
                    f"Период: {months} мес.\n"
                    f"Дата окончания: {end_date}\n\n"
                    "Теперь вы можете делать неограниченное количество запросов для анализа КБЖУ."
                )
                
                bot.send_message(user_id, message_text, parse_mode="Markdown")
        
        return jsonify({"success": True}), 200
    
    except Exception as e:
        logger.error(f"Ошибка при обработке уведомления о платеже: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Обработчик колбека после успешной оплаты
@app.route('/payment_callback', methods=['GET'])
def payment_callback():
    """Обработчик колбека после успешной оплаты"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return "Ошибка: отсутствует идентификатор пользователя", 400
    
    # Страница успешной оплаты
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Оплата успешно выполнена</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                margin-top: 50px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #fff;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #4CAF50;
            }
            .btn {
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                margin-top: 20px;
                text-decoration: none;
                border-radius: 5px;
            }
            p {
                line-height: 1.6;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Оплата успешно выполнена!</h1>
            <p>Спасибо за оформление подписки на бота для анализа КБЖУ по фотографии еды.</p>
            <p>Ваша подписка активирована. Вы можете вернуться в Telegram и продолжить использование бота.</p>
            <a href="https://t.me/YourBotUsername" class="btn">Вернуться в Telegram</a>
        </div>
    </body>
    </html>
    """
    
    return html

# Запуск сервера для обработки вебхуков
if __name__ == "__main__":
    # Удаление старого вебхука, если он существует
    bot.remove_webhook()
    
    # Установка нового вебхука
    url = f"{WEBHOOK_URL}/bot{TELEGRAM_BOT_TOKEN}"
    if WEBHOOK_SSL_CERT:
        bot.set_webhook(url=url, certificate=open(WEBHOOK_SSL_CERT, 'r'))
    else:
        bot.set_webhook(url=url)
    
    # Запуск веб-сервера
    if WEBHOOK_SSL_CERT and WEBHOOK_SSL_PRIV:
        # Запуск с SSL
        app.run(
            host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
            debug=False
        )
    else:
        # Запуск без SSL
        app.run(
            host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            debug=False
        )
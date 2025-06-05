#!/usr/bin/env python3
import os
import sys
import logging
import logging.handlers
from telebot import apihelper
import telebot
import threading
import time
import gc
import psutil
from bot import cleanup_user_data, user_data
from bot import start_cleanup

# Добавляем текущую директорию в PYTHONPATH
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Импортируем конфигурацию и бота
from config import (
    TELEGRAM_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT,
    WEBHOOK_HOST, WEBHOOK_LISTEN, WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV,
    LOG_FILE
)
from bot import bot, logger

# Настройка дополнительного логирования для отладки
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

telebot_logger = logging.getLogger('telebot')
telebot_logger.setLevel(logging.INFO)
telebot_logger.addHandler(file_handler)


def main():
    # Удаляем текущий вебхук, если есть
    logger.info("Удаление текущего вебхука...")
    bot.remove_webhook()

    # Параметры для webhook
    webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}/"
    logger.info(f"Настройка вебхука на {webhook_url}")

    # Устанавливаем вебхук
    bot.set_webhook(
        url=webhook_url,
        certificate=open(WEBHOOK_SSL_CERT, 'rb') if WEBHOOK_SSL_CERT else None
    )

    # Создаем Flask-приложение для обработки webhook
    from flask import Flask, request, abort

    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def home():
        """Красивая главная страница SnapEat"""
        try:
            # Получаем актуальную статистику из БД
            from database.db_manager import DatabaseManager
            health = DatabaseManager.get_database_health()

            # Используем реальные данные или дефолтные
            total_users = health.get('total_users', 9)
            total_analyses = health.get('total_analyses', 150)

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {str(e)}")
            # Fallback значения
            total_users = 9
            total_analyses = 150

        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SnapEat - AI анализ питания | Telegram бот для расчета КБЖУ</title>
    <meta name="description" content="SnapEat - революционный Telegram бот с ИИ для анализа КБЖУ. Фото еды → точный расчет калорий, белков, жиров и углеводов за секунды!">
    <meta name="keywords" content="КБЖУ, калории, питание, диета, анализ еды, ИИ, GPT-4, Telegram бот">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            overflow-x: hidden;
        }}

        /* Animated background */
        .hero {{
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #667eea 100%);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: white;
        }}

        @keyframes gradientShift {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}

        .hero::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="10" r="0.5" fill="white" opacity="0.1"/><circle cx="10" cy="60" r="0.5" fill="white" opacity="0.1"/><circle cx="90" cy="30" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            pointer-events: none;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            position: relative;
            z-index: 1;
        }}

        .hero-content {{
            max-width: 800px;
            margin: 0 auto;
        }}

        .logo {{
            font-size: 5rem;
            margin-bottom: 1rem;
            animation: float 6s ease-in-out infinite;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-20px); }}
        }}

        .hero h1 {{
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 20px rgba(0,0,0,0.3);
            background: linear-gradient(45deg, #fff, #f0f8ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .hero h2 {{
            font-size: 1.5rem;
            font-weight: 300;
            margin-bottom: 2rem;
            opacity: 0.95;
            text-shadow: 1px 1px 10px rgba(0,0,0,0.2);
        }}

        .hero p {{
            font-size: 1.2rem;
            margin-bottom: 3rem;
            opacity: 0.9;
            line-height: 1.8;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }}

        .cta-button {{
            display: inline-block;
            background: linear-gradient(45deg, #ff6b6b, #feca57);
            color: white;
            padding: 18px 40px;
            font-size: 1.2rem;
            font-weight: 600;
            text-decoration: none;
            border-radius: 50px;
            box-shadow: 0 10px 30px rgba(255, 107, 107, 0.4);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .cta-button::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.5s;
        }}

        .cta-button:hover::before {{
            left: 100%;
        }}

        .cta-button:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(255, 107, 107, 0.6);
        }}

        .features {{
            padding: 100px 0;
            background: #f8f9fa;
        }}

        .features-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 40px;
            margin-top: 60px;
        }}

        .feature-card {{
            background: white;
            padding: 40px 30px;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .feature-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(45deg, #667eea, #764ba2);
        }}

        .feature-card:hover {{
            transform: translateY(-10px);
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }}

        .feature-icon {{
            font-size: 3.5rem;
            margin-bottom: 20px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .feature-card h3 {{
            font-size: 1.5rem;
            margin-bottom: 15px;
            color: #333;
        }}

        .feature-card p {{
            color: #666;
            line-height: 1.7;
        }}

        .stats {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 80px 0;
            text-align: center;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 40px;
            margin-top: 50px;
        }}

        .stat-item {{
            text-align: center;
        }}

        .stat-number {{
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #fff, #f0f8ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .stat-label {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}

        .pricing {{
            padding: 100px 0;
            background: white;
            text-align: center;
        }}

        .pricing-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 30px;
            margin-top: 60px;
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
        }}

        .pricing-card {{
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 20px;
            padding: 40px 30px;
            position: relative;
            transition: all 0.3s ease;
        }}

        .pricing-card.featured {{
            border-color: #667eea;
            transform: scale(1.05);
            box-shadow: 0 20px 60px rgba(102, 126, 234, 0.2);
        }}

        .pricing-card.featured::before {{
            content: 'Популярный';
            position: absolute;
            top: -15px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
        }}

        .price {{
            font-size: 3rem;
            font-weight: 700;
            color: #667eea;
            margin: 20px 0;
        }}

        .price-period {{
            font-size: 1rem;
            color: #666;
            font-weight: 400;
        }}

        .features-list {{
            list-style: none;
            padding: 0;
            margin: 30px 0;
        }}

        .features-list li {{
            padding: 10px 0;
            color: #666;
            position: relative;
            padding-left: 30px;
        }}

        .features-list li::before {{
            content: '✓';
            position: absolute;
            left: 0;
            color: #28a745;
            font-weight: bold;
        }}

        .footer {{
            background: #2d3748;
            color: white;
            padding: 60px 0 30px;
            text-align: center;
        }}

        .footer-content {{
            max-width: 800px;
            margin: 0 auto;
        }}

        .status-indicator {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: rgba(40, 167, 69, 0.95);
            color: white;
            padding: 15px 20px;
            border-radius: 50px;
            font-size: 0.9rem;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(40, 167, 69, 0.3);
            backdrop-filter: blur(10px);
            z-index: 1000;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
        }}

        .section-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            text-align: center;
        }}

        .section-subtitle {{
            font-size: 1.2rem;
            color: #666;
            text-align: center;
            max-width: 600px;
            margin: 0 auto;
        }}

        /* Mobile responsiveness */
        @media (max-width: 768px) {{
            .hero h1 {{ font-size: 2.5rem; }}
            .hero h2 {{ font-size: 1.2rem; }}
            .hero p {{ font-size: 1rem; }}
            .logo {{ font-size: 3rem; }}
            .cta-button {{ padding: 15px 30px; font-size: 1rem; }}
            .features {{ padding: 60px 0; }}
            .pricing {{ padding: 60px 0; }}
            .stats {{ padding: 60px 0; }}
            .section-title {{ font-size: 2rem; }}
            .pricing-card.featured {{ transform: none; }}
        }}

        /* Scroll animations */
        .fade-in {{
            opacity: 0;
            transform: translateY(30px);
            transition: all 0.6s ease;
        }}

        .fade-in.visible {{
            opacity: 1;
            transform: translateY(0);
        }}
    </style>
</head>
<body>
    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <div class="hero-content">
                <div class="logo">🤖</div>
                <h1>SnapEat</h1>
                <h2>Революция в анализе питания</h2>
                <p>Сфотографируйте блюдо, запишите голосовое сообщение или опишите текстом — получите точный анализ калорий, белков, жиров и углеводов за секунды с помощью искусственного интеллекта!</p>
                <a href="https://t.me/SnapEatAppBot" class="cta-button">
                    🚀 Начать анализ в Telegram
                </a>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="features">
        <div class="container">
            <h2 class="section-title fade-in">Как это работает?</h2>
            <p class="section-subtitle fade-in">Три простых способа получить анализ КБЖУ</p>

            <div class="features-grid">
                <div class="feature-card fade-in">
                    <div class="feature-icon">📷</div>
                    <h3>Фото еды</h3>
                    <p>GPT-4 Vision анализирует изображение вашего блюда и определяет состав, вес порции и пищевую ценность с высокой точностью</p>
                </div>

                <div class="feature-card fade-in">
                    <div class="feature-icon">🎤</div>
                    <h3>Голосовое сообщение</h3>
                    <p>Опишите что едите голосом — Whisper AI распознает речь, а GPT-4 проанализирует описание и рассчитает КБЖУ</p>
                </div>

                <div class="feature-card fade-in">
                    <div class="feature-icon">📝</div>
                    <h3>Текстовое описание</h3>
                    <p>Просто напишите название блюда — искусственный интеллект мгновенно определит пищевую ценность и размер порции</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Stats Section -->
    <section class="stats">
        <div class="container">
            <h2 class="section-title fade-in">SnapEat в цифрах</h2>
            <div class="stats-grid">
                <div class="stat-item fade-in">
                    <div class="stat-number">{total_users}</div>
                    <div class="stat-label">Активных пользователей</div>
                </div>
                <div class="stat-item fade-in">
                    <div class="stat-number">{total_analyses}+</div>
                    <div class="stat-label">Анализов питания</div>
                </div>
                <div class="stat-item fade-in">
                    <div class="stat-number">3</div>
                    <div class="stat-label">Способа анализа</div>
                </div>
                <div class="stat-item fade-in">
                    <div class="stat-number">99%</div>
                    <div class="stat-label">Точность ИИ</div>
                </div>
            </div>
        </div>
    </section>

    <!-- Pricing Section -->
    <section class="pricing">
        <div class="container">
            <h2 class="section-title fade-in">Простые и честные цены</h2>
            <p class="section-subtitle fade-in">Выберите план, который подходит именно вам</p>

            <div class="pricing-cards">
                <div class="pricing-card fade-in">
                    <h3>Бесплатный</h3>
                    <div class="price">0₽</div>
                    <ul class="features-list">
                        <li>10 анализов еды</li>
                        <li>Все способы анализа</li>
                        <li>Базовая статистика</li>
                        <li>Поддержка в чате</li>
                    </ul>
                    <a href="https://t.me/SnapEatAppBot" class="cta-button">Попробовать</a>
                </div>

                <div class="pricing-card featured fade-in">
                    <h3>Премиум</h3>
                    <div class="price">299₽ <span class="price-period">/месяц</span></div>
                    <ul class="features-list">
                        <li>Неограниченные анализы</li>
                        <li>Персональные нормы КБЖУ</li>
                        <li>Детальная статистика</li>
                        <li>Экспорт данных</li>
                        <li>Приоритетная поддержка</li>
                    </ul>
                    <a href="https://t.me/SnapEatAppBot" class="cta-button">Оформить подписку</a>
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <div class="footer-content">
                <h3>🤖 SnapEat</h3>
                <p>Искусственный интеллект для здорового питания</p>
                <p style="margin-top: 30px; opacity: 0.7;">
                    © 2025 SnapEat. Powered by GPT-4 Vision & Whisper AI
                </p>
            </div>
        </div>
    </footer>

    <!-- Status Indicator -->
    <div class="status-indicator">
        ✅ Bot Online
    </div>

    <!-- Scroll Animation Script -->
    <script>
        // Intersection Observer for fade-in animations
        const observerOptions = {{
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        }};

        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.classList.add('visible');
                }}
            }});
        }}, observerOptions);

        // Observe all fade-in elements
        document.querySelectorAll('.fade-in').forEach(el => {{
            observer.observe(el);
        }});

        // Add some random floating particles
        function createParticle() {{
            const particle = document.createElement('div');
            particle.style.cssText = `
                position: fixed;
                width: 4px;
                height: 4px;
                background: rgba(255,255,255,0.1);
                border-radius: 50%;
                pointer-events: none;
                z-index: 0;
                left: ${{Math.random() * 100}}vw;
                top: 100vh;
                animation: floatUp ${{5 + Math.random() * 5}}s linear forwards;
            `;

            document.body.appendChild(particle);

            setTimeout(() => {{
                particle.remove();
            }}, 10000);
        }}

        // Add CSS for floating animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes floatUp {{
                to {{
                    transform: translateY(-100vh) rotate(360deg);
                    opacity: 0;
                }}
            }}
        `;
        document.head.appendChild(style);

        // Create particles periodically
        setInterval(createParticle, 3000);
    </script>
</body>
</html>''', 200, {'Content-Type': 'text/html; charset=utf-8'}

    @app.route('/status', methods=['GET'])
    def status():
        """Health check endpoint для мониторинга"""
        try:
            from database.db_manager import DatabaseManager
            health = DatabaseManager.get_database_health()
            return f'''<!DOCTYPE html>
<html>
<head>
    <title>SnapEat Bot Status</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f8f9fa; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .status-good {{ color: #28a745; font-size: 1.2rem; }}
        .status-bad {{ color: #dc3545; font-size: 1.2rem; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 25px; }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        .metric {{ font-weight: bold; color: #495057; }}
        .back-link {{ display: inline-block; margin-top: 25px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 25px; }}
        .back-link:hover {{ background: #5a6fd8; }}
        h2 {{ color: #333; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🤖 SnapEat Bot Status</h2>
        <p class="status-good"><strong>Status:</strong> {health['status']} ✅</p>

        <table>
            <tr><td class="metric">Database:</td><td>{health['database_type']}</td></tr>
            <tr><td class="metric">Users:</td><td>{health['total_users']}</td></tr>
            <tr><td class="metric">Analyses:</td><td>{health['total_analyses']}</td></tr>
            <tr><td class="metric">Active Subscriptions:</td><td>{health['active_subscriptions']}</td></tr>
            <tr><td class="metric">Last Check:</td><td>{health['timestamp'][:19]}</td></tr>
        </table>

        <a href="/" class="back-link">← Вернуться на главную</a>
    </div>
</body>
</html>''', 200, {'Content-Type': 'text/html; charset=utf-8'}
        except Exception as e:
            return f'''<!DOCTYPE html>
<html>
<head>
    <title>SnapEat Bot Status - Error</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f8f9fa; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .error {{ color: #dc3545; }}
        .back-link {{ display: inline-block; margin-top: 25px; padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 25px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>❌ SnapEat Bot Status</h2>
        <p class="error"><strong>Status:</strong> Error</p>
        <p class="error"><strong>Error Details:</strong> {str(e)}</p>
        <a href="/" class="back-link">← Вернуться на главную</a>
    </div>
</body>
</html>''', 503, {'Content-Type': 'text/html; charset=utf-8'}

    @app.route(f'/{TELEGRAM_BOT_TOKEN}/', methods=['POST'])
    def webhook():
        logger.info("Получен webhook запрос")
        try:
            if request.headers.get('content-type') == 'application/json':
                json_string = request.get_data().decode('utf-8')
                logger.info(f"Получены данные webhook: {json_string[:100]}...")

                update_dict = apihelper.json.loads(json_string)
                logger.info("JSON успешно разобран")

                update_obj = telebot.types.Update.de_json(update_dict)
                logger.info("Преобразовано в объект Update")

                bot.process_new_updates([update_obj])
                logger.info("Webhook успешно обработан")

                return 'OK'
            else:
                logger.warning(f"Неверный content-type: {request.headers.get('content-type')}")
                abort(403)
        except Exception as e:
            logger.error(f"Ошибка при обработке webhook: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return str(e), 500

    cleanup_thread = threading.Thread(target=cleanup_user_data, daemon=True)
    cleanup_thread.start()
    logger.info("🧹 Запущен фоновый поток очистки user_data")

    start_cleanup()

    logger.info(f"Запуск сервера на {WEBHOOK_LISTEN}:{WEBHOOK_PORT}")


    try:
        app.run(
            host='0.0.0.0',
            port=WEBHOOK_PORT,
            debug=False
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске сервера: {e}")
        raise


if __name__ == "__main__":
    main()
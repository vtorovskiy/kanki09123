# SnapEat - Telegram Bot для анализа КБЖУ

**Версия 2.0** - Telegram-бот для анализа пищевой ценности блюд с помощью искусственного интеллекта.

## 🚀 Основные функции

### 🍽️ **Анализ питания (3 способа):**
- **📷 Фотография еды** - загрузите фото блюда для автоматического анализа через GPT-4 Vision
- **🎤 Голосовое сообщение** - опишите блюдо голосом, бот распознает речь и проанализирует
- **📝 Текстовое описание** - напишите название блюда, и ИИ рассчитает КБЖУ

### 👤 **Персональный подход:**
- Настройка профиля (пол, возраст, вес, рост, уровень активности, цели)
- Автоматический расчет дневных норм КБЖУ по формуле Миффлина-Сан Жеора
- Учет целей: похудение, поддержание веса, набор массы
- Возможность ручного задания персональных норм

### 📊 **Статистика и отслеживание:**
- Автоматическое определение приема пищи по времени (завтрак, обед, ужин, перекус)
- Детальная статистика с разбивкой по дням и приемам пищи
- Удобная навигация по календарю для просмотра истории
- Отображение прогресса относительно дневных норм

### 💳 **Система подписок:**
- **Бесплатно:** 10 анализов для новых пользователей
- **Подписка:** 299 руб/месяц для неограниченного использования
- Гибкие тарифы: 1, 3, 6, 12 месяцев со скидками до 20%
- Безопасная оплата через ЮKassa и Telegram Payments

## 🎯 Новое в версии 2.0

✅ **Удалена функция сканирования штрих-кодов** (упрощение UX)  
✅ **Добавлен анализ голосовых сообщений** через Whisper API  
✅ **Добавлен анализ текстовых описаний** через GPT-4  
✅ **Исправлен баг** с датами в статистике  
✅ **Улучшена точность** распознавания блюд через ИИ  

## 🛠️ Технологический стек

### 🤖 **Искусственный интеллект:**
- **GPT-4 Vision** для анализа изображений еды
- **GPT-4** для анализа текстовых описаний блюд
- **Whisper** для распознавания речи в голосовых сообщениях
- **AITunnel API** как единый провайдер ИИ-сервисов

### 🔧 **Backend:**
- **Python 3.8+** с pyTelegramBotAPI
- **SQLAlchemy** для работы с базой данных SQLite
- **Flask** для обработки webhook'ов и платежей
- **FFmpeg + pydub** для конвертации аудиофайлов

### 📱 **Интерфейс:**
- Интерактивные inline-кнопки
- Система состояний для пошаговых диалогов
- Компактный вывод информации с эмодзи
- Поддержка как polling, так и webhook режимов

### 📊 **Мониторинг:**
- Система сбора метрик (пользователи, API-вызовы, ошибки)
- Отслеживание производительности
- Логирование и отладка

## 📋 Команды бота

- `/start` - Начало работы с ботом, приветствие
- `/help` - Справка по использованию всех функций
- `/stats` - Статистика питания с навигацией по дням
- `/setup` - Настройка профиля и персональных норм КБЖУ
- `/subscription` - Управление подпиской и тарифами
- `/metrics` - Системные метрики (только для администраторов)

## 🚀 Установка и запуск

### 1. Клонирование и установка зависимостей
```bash
git clone <repository-url>
cd nutrition_bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Системные зависимости
```bash
# Для конвертации аудио
sudo apt update
sudo apt install ffmpeg
```

### 3. Настройка окружения
Создайте файл `.env` с настройками:
```env
# Токен Telegram бота
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Ключ API для AITunnel (GPT-4, Whisper)
AITUNNEL_API_KEY=sk-aitunnel-your-key

# Настройки ЮKassa для платежей
PAYMENT_PROVIDER_TOKEN=your_provider_token

# База данных
DATABASE_URL=sqlite:///nutrition_bot.db

# Режим работы (polling для разработки, webhook для продакшена)
BOT_MODE=polling

# Для продакшена (webhook)
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_HOST=yourdomain.com
WEBHOOK_PORT=8443
WEBHOOK_SSL_CERT=/path/to/cert.pem
WEBHOOK_SSL_PRIV=/path/to/private.key

# Логирование
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# ID администраторов
ADMIN_IDS=your_telegram_id
```

### 4. Запуск
```bash
# Разработка (polling)
python bot.py

# Продакшен (webhook)
python run_webhook.py
```

### 5. Настройка как службы (Linux)
```bash
# Создать файл службы
sudo nano /etc/systemd/system/snapeat-bot.service

# Добавить конфигурацию службы
[Unit]
Description=SnapEat Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/nutrition_bot
ExecStart=/path/to/venv/bin/python run_webhook.py
Restart=always

[Install]
WantedBy=multi-user.target

# Запустить службу
sudo systemctl daemon-reload
sudo systemctl enable snapeat-bot.service
sudo systemctl start snapeat-bot.service
```

## 📁 Структура проекта

```
nutrition_bot/
├── bot.py                      # Основной файл бота
├── config.py                   # Конфигурационные параметры
├── run_webhook.py              # Запуск в режиме webhook
├── requirements.txt            # Зависимости Python
├── database/                   # Модуль работы с БД
│   ├── db_manager.py           # Управление базой данных
│   └── models.py               # Модели данных (User, FoodAnalysis, Subscription)
├── food_recognition/           # Модуль анализа еды
│   ├── aitunnel_adapter.py     # Адаптер для AITunnel API
│   ├── aitunnel_vision_api.py  # Взаимодействие с GPT-4 и Whisper
│   ├── nutrition_calc.py       # Резервная база данных продуктов
│   └── vision_api.py           # Google Cloud Vision (резерв)
├── payments/                   # Модуль платежей
│   └── yukassa.py              # Интеграция с ЮKassa
├── monitoring/                 # Модуль мониторинга
│   ├── decorators.py           # Декораторы для отслеживания
│   └── metrics.py              # Сбор и хранение метрик
├── utils/                      # Вспомогательные утилиты
│   ├── helpers.py              # Форматирование и утилиты
│   └── api_helpers.py          # Помощники для работы с API
├── static/                     # Статические файлы
│   ├── start_photo.jpg         # Изображения для команд
│   ├── help.jpg
│   ├── setup.jpg
│   └── subscription.jpg
├── logs/                       # Логи приложения
└── data/                       # Данные (метрики, резервные копии)
```

## 🔧 Основные API и интеграции

### AITunnel API
- **GPT-4 Vision** - анализ изображений еды
- **GPT-4** - анализ текстовых описаний
- **Whisper** - распознавание речи

### Telegram Bot API
- Webhook и Polling режимы
- Inline-клавиатуры и состояния
- Обработка фото, голоса, текста

### ЮKassa + Telegram Payments
- Прием платежей за подписку
- Автоматическая активация доступа
- Поддержка различных тарифов

## 📊 Мониторинг и метрики

Бот собирает следующие метрики:
- Количество уникальных пользователей
- Анализы фотографий, голоса, текста
- Время ответа API и частота ошибок
- Покупки подписок
- Популярные команды

Просмотр метрик: `/metrics` (только для администраторов)

## 🔄 Управление службой

```bash
# Статус службы
sudo systemctl status snapeat-bot.service

# Перезапуск
sudo systemctl restart snapeat-bot.service

# Просмотр логов
sudo journalctl -u snapeat-bot.service -f

# Логи приложения
tail -f /path/to/nutrition_bot/logs/bot.log
```

## 📈 Планы развития

- 🔗 Интеграция с фитнес-трекерами (MyFitnessPal, Apple Health)
- 📊 Расширенная аналитика с графиками
- 🥗 Рекомендации рецептов на основе предпочтений
- 🌍 Поддержка других языков
- 📱 Мобильное приложение-компаньон

## 🤝 Поддержка

Для вопросов и предложений обращайтесь к администратору бота или создавайте issue в репозитории.

---

**SnapEat v2.0** - Ваш персональный ИИ-диетолог в Telegram! 🤖🍽️
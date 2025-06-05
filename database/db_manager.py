from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy import text, func
from datetime import datetime, timedelta, time
import sys
import os
import logging
import functools
from contextlib import contextmanager

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FREE_REQUESTS_LIMIT, IS_POSTGRESQL
from database.models import User, UserSubscription, FoodAnalysis, init_db
from monitoring.decorators import track_api_call

logger = logging.getLogger(__name__)

# Инициализация базы данных и сессий
engine = init_db()
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def determine_meal_type(time):
    """
    Определяет тип приема пищи по времени

    Args:
        time (datetime): Время приема пищи

    Returns:
        str: Тип приема пищи (breakfast, lunch, dinner, snack)
    """
    hour = time.hour

    if 5 <= hour < 11:
        return "breakfast"  # Завтрак: 5:00 - 10:59
    elif 11 <= hour < 16:
        return "lunch"  # Обед: 11:00 - 15:59
    elif 16 <= hour < 21:
        return "dinner"  # Ужин: 16:00 - 20:59
    else:
        return "snack"  # Перекус: 21:00 - 4:59


def db_retry(max_retries=3, retry_delay=0.5):
    """
    Декоратор для повторных попыток при ошибках БД
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, IntegrityError) as e:
                    last_exception = e
                    error_msg = str(e).lower()

                    # Определяем, стоит ли повторять попытку
                    if any(keyword in error_msg for keyword in [
                        'database is locked', 'connection', 'timeout',
                        'deadlock', 'serialization failure'
                    ]):
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Database retry {attempt + 1}/{max_retries} for {func.__name__}: {str(e)}")
                            import time
                            time.sleep(wait_time)
                            continue

                    # Не повторяем для других типов ошибок
                    logger.error(f"Database error in {func.__name__}: {str(e)}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise

            # Если все попытки исчерпаны
            logger.error(f"All {max_retries} retries failed for {func.__name__}")
            raise last_exception

        return wrapper

    return decorator


@contextmanager
def get_db_session():
    """
    Context manager для безопасной работы с сессией БД
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        session.close()


class DatabaseManager:
    """Класс для управления базой данных с оптимизированными запросами"""

    @staticmethod
    @db_retry(max_retries=3)
    def get_user_profile(telegram_id):
        """
        Получает профиль пользователя
        """
        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return None

            return {
                'gender': user.gender,
                'age': user.age,
                'weight': user.weight,
                'height': user.height,
                'activity_level': user.activity_level,
                'daily_calories': user.daily_calories,
                'daily_proteins': user.daily_proteins,
                'daily_fats': user.daily_fats,
                'daily_carbs': user.daily_carbs
            }

    @staticmethod
    def calculate_daily_norms(gender, age, weight, height, activity_level, goal='maintenance'):
        """
        Рассчитывает рекомендуемые дневные нормы КБЖУ по формуле Миффлина-Сан Жеора
        """
        # Расчет базового метаболизма (BMR)
        if gender == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:  # female
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        # Расчет суточной потребности в калориях
        daily_calories = bmr * activity_level

        # Корректировка в зависимости от цели
        if goal == 'weight_loss':
            daily_calories *= 0.8
        elif goal == 'weight_gain':
            daily_calories *= 1.15

        # Расчет макронутриентов
        if goal == 'weight_loss':
            protein_ratio, fat_ratio, carb_ratio = 0.35, 0.30, 0.35
        elif goal == 'weight_gain':
            protein_ratio, fat_ratio, carb_ratio = 0.30, 0.25, 0.45
        else:  # maintenance
            protein_ratio, fat_ratio, carb_ratio = 0.30, 0.30, 0.40

        daily_proteins = (daily_calories * protein_ratio) / 4
        daily_fats = (daily_calories * fat_ratio) / 9
        daily_carbs = (daily_calories * carb_ratio) / 4

        return {
            'daily_calories': round(daily_calories, 1),
            'daily_proteins': round(daily_proteins, 1),
            'daily_fats': round(daily_fats, 1),
            'daily_carbs': round(daily_carbs, 1)
        }

    @staticmethod
    @db_retry(max_retries=3)
    def update_user_profile(telegram_id, **kwargs):
        """
        Обновляет профиль пользователя с автоматическим расчетом норм
        """
        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return None

            # Обновляем переданные поля
            for field, value in kwargs.items():
                if hasattr(user, field) and value is not None:
                    setattr(user, field, value)

            # Автоматический расчет норм, если все параметры указаны
            if (user.gender and user.age and user.weight and user.height and user.activity_level and
                    'daily_calories' not in kwargs):
                goal = user.goal or 'maintenance'
                norms = DatabaseManager.calculate_daily_norms(
                    user.gender, user.age, user.weight, user.height, user.activity_level, goal
                )

                user.daily_calories = norms['daily_calories']
                user.daily_proteins = norms['daily_proteins']
                user.daily_fats = norms['daily_fats']
                user.daily_carbs = norms['daily_carbs']

            # Возвращаем текущие нормы
            return {
                'daily_calories': user.daily_calories,
                'daily_proteins': user.daily_proteins,
                'daily_fats': user.daily_fats,
                'daily_carbs': user.daily_carbs
            }

    @staticmethod
    @db_retry(max_retries=3)
    def get_user_daily_norms(telegram_id):
        """
        Получает дневные нормы КБЖУ пользователя
        """
        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user or not user.daily_calories:
                return None

            return {
                'daily_calories': user.daily_calories,
                'daily_proteins': user.daily_proteins,
                'daily_fats': user.daily_fats,
                'daily_carbs': user.daily_carbs,
                'has_full_profile': bool(
                    user.gender and user.age and user.weight and
                    user.height and user.activity_level
                )
            }

    @staticmethod
    @db_retry(max_retries=3)
    def get_or_create_user(telegram_id, username=None, first_name=None, last_name=None):
        """
        Получить или создать пользователя (оптимизированная версия)
        """
        with get_db_session() as session:
            # Сначала пытаемся найти существующего пользователя
            user = session.query(User).filter_by(telegram_id=telegram_id).first()

            if not user:
                # Создаем нового пользователя
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.flush()  # Получаем ID без commit
                logger.info(f"Created new user: {telegram_id}")

            return user

    @staticmethod
    @db_retry(max_retries=3)
    def get_nutrition_stats_for_date(telegram_id, date):
        """
        Оптимизированное получение статистики за дату
        """
        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return None

            # Определяем границы дня
            start_of_day = datetime.combine(date, time.min)
            end_of_day = datetime.combine(date, time.max)

            # Один оптимизированный запрос вместо множественных
            analyses = session.query(FoodAnalysis).filter(
                FoodAnalysis.user_id == user.id,
                FoodAnalysis.analysis_date >= start_of_day,
                FoodAnalysis.analysis_date <= end_of_day
            ).order_by(FoodAnalysis.analysis_date).all()

            # Инициализация статистики
            meal_stats = {
                meal_type: {"count": 0, "calories": 0, "proteins": 0, "fats": 0, "carbs": 0, "items": []}
                for meal_type in ["breakfast", "lunch", "dinner", "snack"]
            }
            meal_stats["total"] = {"count": 0, "calories": 0, "proteins": 0, "fats": 0, "carbs": 0, "items": []}

            # Обработка результатов
            for analysis in analyses:
                meal_type = analysis.meal_type or "snack"

                # Обновляем статистику по типу приема пищи
                meal_stats[meal_type]["count"] += 1
                meal_stats[meal_type]["calories"] += analysis.calories or 0
                meal_stats[meal_type]["proteins"] += analysis.proteins or 0
                meal_stats[meal_type]["fats"] += analysis.fats or 0
                meal_stats[meal_type]["carbs"] += analysis.carbs or 0

                # Добавляем информацию о блюде
                item_info = {
                    "name": analysis.food_name,
                    "calories": analysis.calories,
                    "proteins": analysis.proteins,
                    "fats": analysis.fats,
                    "carbs": analysis.carbs,
                    "time": analysis.analysis_date.strftime("%H:%M"),
                    "portion_weight": analysis.portion_weight
                }
                meal_stats[meal_type]["items"].append(item_info)

                # Обновляем общую статистику
                meal_stats["total"]["count"] += 1
                meal_stats["total"]["calories"] += analysis.calories or 0
                meal_stats["total"]["proteins"] += analysis.proteins or 0
                meal_stats["total"]["fats"] += analysis.fats or 0
                meal_stats["total"]["carbs"] += analysis.carbs or 0
                meal_stats["total"]["items"].append(item_info)

            # Округляем значения
            for meal_type in meal_stats:
                for nutrient in ["calories", "proteins", "fats", "carbs"]:
                    meal_stats[meal_type][nutrient] = round(meal_stats[meal_type][nutrient], 1)

            return meal_stats

    @staticmethod
    @track_api_call('db_save_food_analysis')
    @db_retry(max_retries=3)
    def save_food_analysis(telegram_id, food_name, calories, proteins, fats, carbs,
                           image_path=None, portion_weight=None, analysis_time=None):
        """
        Оптимизированное сохранение анализа еды
        """
        with get_db_session() as session:
            # Получаем или создаем пользователя в одной транзакции
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id)
                session.add(user)
                session.flush()  # Получаем ID пользователя

            # Определяем время и тип приема пищи
            if analysis_time is None:
                analysis_time = datetime.utcnow()

            meal_type = determine_meal_type(analysis_time)

            # Создаем анализ
            food_analysis = FoodAnalysis(
                user_id=user.id,
                food_name=food_name,
                calories=calories,
                proteins=proteins,
                fats=fats,
                carbs=carbs,
                image_path=image_path,
                portion_weight=portion_weight,
                analysis_date=analysis_time,
                meal_type=meal_type
            )

            session.add(food_analysis)
            session.flush()  # Получаем ID анализа

            analysis_id = food_analysis.id
            logger.info(f"Saved food analysis {analysis_id} for user {telegram_id}")

            return analysis_id

    @staticmethod
    @db_retry(max_retries=3)
    def check_subscription_status(telegram_id):
        """
        ИСПРАВЛЕННАЯ проверка статуса подписки с автоочисткой
        """
        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                return False

            # Московское время (UTC+3)
            now_msk = datetime.utcnow() + timedelta(hours=3)

            # Находим и деактивируем истекшие подписки этого пользователя
            expired_subscriptions = session.query(UserSubscription).filter(
                UserSubscription.user_id == user.id,
                UserSubscription.is_active == True,
                UserSubscription.end_date <= now_msk
            ).all()

            # Деактивируем истекшие подписки
            for subscription in expired_subscriptions:
                subscription.is_active = False
                logger.info(f"Деактивирована истекшая подписка для пользователя {telegram_id}")

            # ИСПРАВЛЕНИЕ: Сначала commit изменений
            if expired_subscriptions:
                session.commit()

            # Проверяем есть ли активные подписки (ПОСЛЕ commit'а)
            active_subscription = session.query(UserSubscription).filter(
                UserSubscription.user_id == user.id,
                UserSubscription.is_active == True,
                UserSubscription.end_date > now_msk
            ).first()

            return bool(active_subscription)

    @staticmethod
    @track_api_call('db_add_subscription')
    @db_retry(max_retries=3)
    def add_subscription(telegram_id, months=1, payment_id=None):
        """
        Добавить подписку пользователю
        """
        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id)
                session.add(user)
                session.flush()

            end_date = datetime.utcnow() + timedelta(days=30 * months)

            subscription = UserSubscription(
                user_id=user.id,
                end_date=end_date,
                payment_id=payment_id
            )

            session.add(subscription)
            session.flush()

            logger.info(f"Added subscription for user {telegram_id}, {months} months")
            return subscription

    @staticmethod
    @db_retry(max_retries=3)
    def get_remaining_free_requests(telegram_id):
        """
        Оптимизированное получение оставшихся бесплатных запросов
        """
        # Сначала проверяем подписку
        if DatabaseManager.check_subscription_status(telegram_id):
            return float('inf')

        with get_db_session() as session:
            # Подсчитываем использованные запросы одним запросом
            used_requests = session.query(FoodAnalysis).join(User).filter(
                User.telegram_id == telegram_id
            ).count()

            remaining = max(0, FREE_REQUESTS_LIMIT - used_requests)
            return remaining

    @staticmethod
    @db_retry(max_retries=3)
    def get_user_statistics(telegram_id):
        """
        Оптимизированная общая статистика пользователя
        """
        with get_db_session() as session:
            # Используем агрегацию на уровне БД вместо Python
            stats = session.query(
                func.count(FoodAnalysis.id).label('total_analyses'),
                func.coalesce(func.sum(FoodAnalysis.calories), 0).label('total_calories'),
                func.coalesce(func.sum(FoodAnalysis.proteins), 0).label('total_proteins'),
                func.coalesce(func.sum(FoodAnalysis.fats), 0).label('total_fats'),
                func.coalesce(func.sum(FoodAnalysis.carbs), 0).label('total_carbs')
            ).join(User).filter(User.telegram_id == telegram_id).first()

            if not stats:
                return None

            return {
                "total_analyses": stats.total_analyses,
                "total_calories": round(float(stats.total_calories), 1),
                "total_proteins": round(float(stats.total_proteins), 1),
                "total_fats": round(float(stats.total_fats), 1),
                "total_carbs": round(float(stats.total_carbs), 1)
            }

    @staticmethod
    @db_retry(max_retries=3)
    def get_earliest_analysis_date(telegram_id):
        """
        Получить дату самого раннего анализа пользователя
        """
        with get_db_session() as session:
            earliest = session.query(func.min(FoodAnalysis.analysis_date)).join(User).filter(
                User.telegram_id == telegram_id
            ).scalar()

            return earliest.date() if earliest else None

    @staticmethod
    @db_retry(max_retries=3)
    def has_data_for_date(telegram_id, date):
        """
        Проверяет наличие данных за дату (оптимизированная версия)
        """
        with get_db_session() as session:
            start_of_day = datetime.combine(date, time.min)
            end_of_day = datetime.combine(date, time.max)

            count = session.query(FoodAnalysis).join(User).filter(
                User.telegram_id == telegram_id,
                FoodAnalysis.analysis_date >= start_of_day,
                FoodAnalysis.analysis_date <= end_of_day
            ).count()

            return count > 0

    @staticmethod
    def get_database_health():
        """
        Проверка состояния базы данных
        """
        try:
            with get_db_session() as session:
                # Простой запрос для проверки соединения (исправлено для SQLAlchemy 2.0)
                from sqlalchemy import text
                session.execute(text("SELECT 1"))

                # Получаем статистику использования
                if IS_POSTGRESQL:
                    # PostgreSQL специфичные запросы
                    result = session.execute(text("""
                                                  SELECT (SELECT COUNT(*) FROM users)                                     as total_users,
                                                         (SELECT COUNT(*) FROM food_analyses)                             as total_analyses,
                                                         (SELECT COUNT(*) FROM user_subscriptions WHERE is_active = true) as active_subscriptions
                                                  """)).fetchone()

                    total_users, total_analyses, active_subscriptions = result
                else:
                    # SQLite совместимый запрос
                    users_count = session.query(User).count()
                    analyses_count = session.query(FoodAnalysis).count()
                    subscriptions_count = session.query(UserSubscription).filter_by(is_active=True).count()
                    total_users, total_analyses, active_subscriptions = users_count, analyses_count, subscriptions_count

                return {
                    'status': 'healthy',
                    'database_type': 'PostgreSQL' if IS_POSTGRESQL else 'SQLite',
                    'total_users': total_users,
                    'total_analyses': total_analyses,
                    'active_subscriptions': active_subscriptions,
                    'timestamp': datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'total_users': 0,
                'total_analyses': 0,
                'active_subscriptions': 0
            }

    @staticmethod
    def cleanup_old_data(days_to_keep=90):
        """
        Очистка старых данных (для оптимизации производительности)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            with get_db_session() as session:
                # Удаляем старые анализы еды
                deleted_analyses = session.query(FoodAnalysis).filter(
                    FoodAnalysis.analysis_date < cutoff_date
                ).delete(synchronize_session=False)

                # Удаляем неактивные подписки старше cutoff_date
                deleted_subscriptions = session.query(UserSubscription).filter(
                    UserSubscription.is_active == False,
                    UserSubscription.end_date < cutoff_date
                ).delete(synchronize_session=False)

                logger.info(
                    f"Cleanup completed: {deleted_analyses} analyses, {deleted_subscriptions} subscriptions deleted")

                return {
                    'deleted_analyses': deleted_analyses,
                    'deleted_subscriptions': deleted_subscriptions,
                    'cutoff_date': cutoff_date.isoformat()
                }

        except Exception as e:
            logger.error(f"Data cleanup failed: {str(e)}")
            raise
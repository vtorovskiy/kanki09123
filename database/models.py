from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, ForeignKey, create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.pool import QueuePool
from datetime import datetime
import sys
import os
import logging

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL, IS_POSTGRESQL, DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT, DB_POOL_RECYCLE

logger = logging.getLogger(__name__)

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)  # Изменено на BigInteger
    username = Column(String(255), nullable=True)  # Ограничена длина для PostgreSQL
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    registration_date = Column(DateTime, default=datetime.utcnow, index=True)  # Добавлен индекс

    # Поля для дневных норм КБЖУ
    gender = Column(String(10), nullable=True)  # 'male' или 'female'
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)  # в кг
    height = Column(Float, nullable=True)  # в см
    activity_level = Column(Float, nullable=True)  # коэффициент активности (1.2 - 1.9)
    goal = Column(String(20), nullable=True)  # 'weight_loss', 'maintenance', 'weight_gain'

    # Расчетные нормы (могут быть заданы вручную или расчитаны)
    daily_calories = Column(Float, nullable=True)
    daily_proteins = Column(Float, nullable=True)
    daily_fats = Column(Float, nullable=True)
    daily_carbs = Column(Float, nullable=True)

    # Отношения
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    food_analyses = relationship("FoodAnalysis", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class UserSubscription(Base):
    """Модель подписки пользователя"""
    __tablename__ = 'user_subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    start_date = Column(DateTime, default=datetime.utcnow, index=True)
    end_date = Column(DateTime, nullable=False, index=True)  # Часто используется в запросах
    is_active = Column(Boolean, default=True, index=True)
    payment_id = Column(String(255), nullable=True, index=True)

    # Отношения
    user = relationship("User", back_populates="subscriptions")

    # Составной индекс для быстрого поиска активных подписок
    __table_args__ = (
        Index('idx_active_subscriptions', 'user_id', 'is_active', 'end_date'),
    )

    def __repr__(self):
        return f"<UserSubscription(user_id={self.user_id}, active={self.is_active}, end_date={self.end_date})>"


class FoodAnalysis(Base):
    """Модель анализа пищи"""
    __tablename__ = 'food_analyses'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    analysis_date = Column(DateTime, default=datetime.utcnow, index=True)  # Часто используется в запросах
    food_name = Column(String(500), nullable=True)  # Увеличена длина
    calories = Column(Float, nullable=True)
    proteins = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    image_path = Column(String(1000), nullable=True)  # Путь к изображению
    portion_weight = Column(Float, nullable=True)  # Вес порции
    meal_type = Column(String(20), nullable=True, index=True)  # 'breakfast', 'lunch', 'dinner', 'snack'

    # Отношения
    user = relationship("User", back_populates="food_analyses")

    # Составные индексы для оптимизации запросов статистики
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'analysis_date'),
        Index('idx_user_meal_date', 'user_id', 'meal_type', 'analysis_date'),
    )

    def __repr__(self):
        return f"<FoodAnalysis(id={self.id}, food_name={self.food_name}, calories={self.calories})>"


def create_database_engine():
    """
    Создание engine базы данных с оптимальными настройками
    """
    try:
        if IS_POSTGRESQL:
            # PostgreSQL с connection pooling
            engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=DB_POOL_SIZE,
                max_overflow=DB_MAX_OVERFLOW,
                pool_timeout=DB_POOL_TIMEOUT,
                pool_recycle=DB_POOL_RECYCLE,
                pool_pre_ping=True,  # Проверка соединений
                echo=False,  # Отключаем SQL логи в продакшене
                future=True  # Используем новый стиль SQLAlchemy 2.0
            )
            logger.info(f"PostgreSQL engine created with pool_size={DB_POOL_SIZE}")
        else:
            # SQLite fallback (для разработки)
            engine = create_engine(
                DATABASE_URL,
                pool_timeout=DB_POOL_TIMEOUT,
                echo=False,
                future=True,
                # SQLite специфичные настройки
                connect_args={
                    "check_same_thread": False,
                    "timeout": 20
                }
            )
            logger.info("SQLite engine created (fallback mode)")

        return engine

    except Exception as e:
        logger.error(f"Failed to create database engine: {str(e)}")
        raise


# Инициализация базы данных
def init_db():
    """
    Инициализация базы данных с созданием всех таблиц
    """
    try:
        engine = create_database_engine()

        # Создание всех таблиц
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")

        return engine

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


def get_database_info():
    """
    Получение информации о текущей конфигурации базы данных
    """
    return {
        'database_type': 'PostgreSQL' if IS_POSTGRESQL else 'SQLite',
        'database_url': DATABASE_URL.split('@')[0] + '@***' if '@' in DATABASE_URL else 'SQLite file',
        'pool_size': DB_POOL_SIZE if IS_POSTGRESQL else 'N/A',
        'max_overflow': DB_MAX_OVERFLOW if IS_POSTGRESQL else 'N/A',
        'pool_timeout': DB_POOL_TIMEOUT
    }
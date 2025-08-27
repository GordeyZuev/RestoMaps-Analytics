from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base
from config.settings import settings
from logger import logger

DATABASE_URL = settings.database_url
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_database_if_not_exists():
    """Создание базы данных, если она не существует"""
    postgres_url = settings.postgres_url

    try:
        temp_engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")

        with temp_engine.connect() as conn:
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{settings.POSTGRES_DB}'"))
            if not result.fetchone():
                conn.execute(text(f"CREATE DATABASE {settings.POSTGRES_DB}"))
                logger.success(f"Создана база данных: {settings.POSTGRES_DB}")
            else:
                logger.info(f"База данных уже существует: {settings.POSTGRES_DB}")

    except Exception:
        logger.exception("Ошибка при создании базы данных. Проверьте подключение к PostgreSQL и настройки")


def create_tables():
    """Создание всех таблиц в базе данных"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(auto_create_db: bool = False):
    """
    Инициализация базы данных

    Args:
        auto_create_db: если True, автоматически создает БД если её нет
                       если False, только создает таблицы в существующей БД
    """
    logger.info("Инициализация базы данных начата")
    if auto_create_db:
        create_database_if_not_exists()
    create_tables()
    logger.success("База данных инициализирована")


def reset_database():
    """Сброс и пересоздание базы данных"""
    logger.warning("Запущен сброс и пересоздание базы данных")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_restaurants_notion_id ON restaurants(notion_id);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants(city);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_restaurants_visited ON restaurants(visited);"))
        db.commit()
        logger.success("База данных пересоздана и индексы созданы")
    except Exception:
        logger.exception("Ошибка при создании индексов после пересоздания базы данных")
    finally:
        db.close()





if __name__ == "__main__":
    reset_database()

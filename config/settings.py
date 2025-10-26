import os

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv("config/.env")


class Settings:
    """Настройки приложения"""

    # База данных
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "restomaps_analytics")

    # API ключи
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    YA_GEO_CODER_API_KEY = os.getenv("YA_GEO_CODER_API_KEY")

    # Логирование
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    SENTRY_DSN = os.getenv("SENTRY_DSN")

    @property
    def database_url(self):
        """URL подключения к базе данных"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def postgres_url(self):
        """URL для подключения к PostgreSQL (без указания БД)"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/postgres"


# Глобальный экземпляр настроек
settings = Settings()

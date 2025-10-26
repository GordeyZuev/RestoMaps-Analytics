from pathlib import Path
import sys

from loguru import logger
import sentry_sdk
from sentry_sdk import capture_exception


def get_log_level_from_env() -> str:
    """Получить уровень логирования из переменных окружения

    Returns:
        Уровень логирования (по умолчанию INFO)
    """
    from config.settings import settings

    return settings.LOG_LEVEL


def setup_sentry() -> None:
    """Настройка Sentry"""
    from config.settings import settings

    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN)


def sentry_sink(message) -> None:
    """Sink для отправки ошибок в Sentry"""
    if (message.record["level"].name in ["ERROR", "CRITICAL"]
        and message.record["exception"]):
        capture_exception(message.record["exception"])


def setup_logger(
    log_level: str | None = None,
    enable_console: bool = True,
    enable_file: bool = True,
    log_to_stdout: bool = False,
) -> None:
    """Настройка системы логирования"""
    if log_level is None:
        log_level = get_log_level_from_env()

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    logger.remove()

    console_format = (
        "<green>{time:HH:mm:ss}</green> | <level>{level: <4}</level> | "
        "<level>{message}</level>"
    )
    # Подробный формат для файлов
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    )

    if enable_console:
        logger.add(
            sys.stdout if log_to_stdout else sys.stderr,
            format=console_format,
            level=log_level,
            colorize=True,
            # Убираем backtrace и diagnose для консоли
            backtrace=False,
            diagnose=False,
        )

    if enable_file:
        logger.add(
            logs_dir / "app.log",
            format=file_format,
            level=log_level,
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

        logger.add(
            logs_dir / "errors.log",
            format=file_format,
            level="ERROR",
            rotation="5 MB",
            retention="60 days",
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

    setup_sentry()

    from config.settings import settings

    if settings.SENTRY_DSN:
        logger.add(sentry_sink, level="ERROR")


def get_logger(name: str | None = None) -> logger:
    """Получить настроенный логгер"""
    if name:
        return logger.bind(name=name)
    return logger


setup_logger(log_level=None, enable_console=True, enable_file=True)

__all__ = ["logger", "get_logger", "setup_logger", "get_log_level_from_env"]

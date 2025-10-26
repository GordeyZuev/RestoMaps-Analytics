from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import click

from core.job_manager import get_job_manager
from database.database import init_db as db_init_db
from logger import logger
from parsers.notion_data import sync_notion_data
from parsers.ya_maps_reviews_parser import fetch_reviews_for_all_restaurants

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def find_free_port(start_port: int = 8501, max_attempts: int = 10) -> int | None:
    """Найти свободный порт начиная с start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    return None


def run_ui() -> None:
    """Запускает веб-интерфейс Streamlit"""
    logger.info("Запуск веб-интерфейса...")

    try:
        port = find_free_port()
        if port is None:
            logger.error("Не удалось найти свободный порт для Streamlit")
            return

        logger.info(f"Запуск на порту {port}")

        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "core/app.py",
                f"--server.port={port}",
                "--server.address=0.0.0.0",
                "--server.headless=true",
                "--browser.gatherUsageStats=false",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка запуска Streamlit: {e}")


def run_notion_sync() -> None:
    """Синхронизация данных с Notion"""
    logger.info("Синхронизация с Notion...")

    try:
        result = sync_notion_data()
        if result:
            logger.success("Синхронизация завершена")
        else:
            logger.error("Ошибка синхронизации")
    except Exception as e:
        logger.error(f"Ошибка: {e}")


def run_init_db() -> None:
    """Инициализация базы данных"""
    logger.info("Инициализация базы данных...")

    try:
        db_init_db(auto_create_db=True)
        logger.success("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")


def run_reviews_parsing(limit_restaurants: int | None = 50) -> None:
    """Парсинг отзывов с Яндекс.Карт"""
    try:
        result = fetch_reviews_for_all_restaurants(limit_restaurants=limit_restaurants)

        if result.get("success"):
            logger.success("Парсинг завершен")
        else:
            logger.error(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Ошибка: {e}")


def run_nlp_processing() -> None:
    """NLP обработка отзывов"""
    try:
        manager = get_job_manager()
        result = manager.run_job_now("nlp_processing")

        if result.get("success"):
            logger.success("NLP обработка завершена")
        else:
            logger.error(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Ошибка: {e}")


def run_failed_restaurants_check(limit_restaurants: int | None = 20) -> None:
    """Повторная проверка ресторанов с ошибками"""
    try:
        from parsers.ya_maps_reviews_parser import fetch_reviews_for_failed_restaurants

        result = fetch_reviews_for_failed_restaurants(limit_restaurants=limit_restaurants)

        if result.get("success"):
            logger.success("Повторная проверка завершена")
        else:
            logger.error(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Ошибка: {e}")


def run_initial_full_cycle() -> None:
    """Запускает полный первоначальный цикл для всех ресторанов"""
    logger.info("Запуск полного первоначального цикла...")
    logger.info("Обрабатываются ВСЕ рестораны без ограничений")

    try:
        # Этап 1: Синхронизация с Notion
        logger.info("\n" + "=" * 60)
        logger.info("ЭТАП 1/4: Синхронизация с Notion")
        logger.info("=" * 60)
        run_notion_sync()

        # Этап 2: Парсинг отзывов для ВСЕХ ресторанов
        logger.info("\n" + "=" * 60)
        logger.info("ЭТАП 2/4: Парсинг отзывов для всех ресторанов")
        logger.info("=" * 60)
        run_reviews_parsing(limit_restaurants=None)  # Без лимита

        # Этап 3: NLP обработка
        logger.info("\n" + "=" * 60)
        logger.info("ЭТАП 3/4: NLP обработка отзывов")
        logger.info("=" * 60)
        run_nlp_processing()

        # Этап 4: Запуск планировщика для регулярных задач
        logger.info("\n" + "=" * 60)
        logger.info("ЭТАП 4/4: Запуск планировщика для регулярных задач")
        logger.info("=" * 60)
        logger.info("Планировщик будет выполнять задачи по расписанию:")
        logger.info("   - Notion sync: каждый день в 06:00")
        logger.info("   - Reviews parsing: каждый день в 08:00")
        logger.info("   - NLP processing: каждый день в 09:00")

        # Запускаем планировщик (это блокирующий вызов)
        run_scheduler()

    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка в первоначальном цикле: {e}")


def run_scheduler() -> None:
    """Запускает планировщик задач"""
    logger.info("Запуск планировщика задач...")

    try:
        manager = get_job_manager()
        manager.start()
        logger.success("Планировщик запущен")
        logger.info("Джобы будут выполняться по расписанию:")
        logger.info("   - Notion sync: каждый день в 06:00")
        logger.info("   - Reviews parsing: каждый день в 08:00")
        logger.info("   - NLP processing: каждый день в 09:00")

        def signal_handler(_signum, _frame):
            logger.info("Остановка планировщика...")
            manager.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
        manager.stop()
    except Exception as e:
        logger.error(f"Ошибка планировщика: {e}")
        if "manager" in locals():
            manager.stop()


def run_full() -> None:
    """Запускает полный цикл: Scheduler + Notion -> UI -> Reviews (в фоне)"""
    logger.info("Запуск полного цикла...")

    try:
        # Запускаем планировщик в фоне
        logger.info("Запуск планировщика в фоновом режиме...")
        scheduler_process = subprocess.Popen(
            [sys.executable, __file__, "--scheduler"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Планировщик запущен в фоне")

        logger.info("Этап 1/3: Синхронизация с Notion")
        run_notion_sync()

        logger.info("Этап 2/3: Запуск фонового парсинга отзывов...")
        subprocess.Popen(
            [sys.executable, __file__, "--reviews"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Парсинг запущен в фоне")

        logger.info("Этап 3/3: Запуск веб-интерфейса")
        logger.info("Планировщик и парсинг работают в фоновом режиме")
        run_ui()

    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
        if "scheduler_process" in locals():
            scheduler_process.terminate()
    except Exception as e:
        logger.error(f"Ошибка в полном цикле: {e}")
        if "scheduler_process" in locals():
            scheduler_process.terminate()


@click.group()
@click.version_option(version="1.0.0")
@click.pass_context
def cli(ctx):
    """RestoMaps Analytics - Система аналитики ресторанов"""
    ctx.ensure_object(dict)
    logger.info("RestoMaps Analytics")


@cli.command()
@click.option("--limit", "-l", type=int, help="Ограничить количество обрабатываемых ресторанов")
def reviews(limit):
    """Парсить отзывы из Яндекс.Карт"""
    click.echo(click.style("🍽️  Парсинг отзывов из Яндекс.Карт", fg="blue", bold=True))
    run_reviews_parsing(limit_restaurants=limit)


@cli.command()
def notion():
    """Синхронизировать данные с Notion"""
    click.echo(click.style("📝 Синхронизация с Notion", fg="green", bold=True))
    run_notion_sync()


@cli.command()
def init_db():
    """Инициализировать базу данных"""
    click.echo(click.style("🗄️  Инициализация базы данных", fg="yellow", bold=True))
    run_init_db()


@cli.command()
@click.option("--limit", "-l", type=int, default=20, help="Ограничить количество проверяемых ресторанов")
def check_failed(limit):
    """Повторная проверка ресторанов с ошибками"""
    click.echo(click.style("🔧 Повторная проверка ресторанов с ошибками", fg="red", bold=True))
    run_failed_restaurants_check(limit_restaurants=limit)


@cli.command()
def scheduler():
    """Запустить планировщик задач"""
    click.echo(click.style("⏰ Запуск планировщика задач", fg="cyan", bold=True))
    run_scheduler()


@cli.command()
def ui():
    """Запустить веб-интерфейс"""
    click.echo(click.style("🌐 Запуск веб-интерфейса", fg="magenta", bold=True))
    run_ui()


@cli.command()
def full():
    """Полный цикл: Scheduler + Notion + Reviews + UI"""
    click.echo(click.style("🚀 Полный цикл: Scheduler + Notion + Reviews + UI", fg="bright_green", bold=True))
    run_full()


@cli.command()
def initial():
    """Полный первоначальный прогон для всех ресторанов + планировщик"""
    click.echo(click.style("🎯 Полный первоначальный прогон для всех ресторанов + планировщик", fg="bright_yellow", bold=True))
    run_initial_full_cycle()


if __name__ == "__main__":
    cli()

from typing import Optional
from database.database import init_db as db_init_db
from core.job_manager import get_job_manager
from parsers.ya_maps_reviews_parser import fetch_reviews_for_all_restaurants
from parsers.notion_data import sync_notion_data
from logger import logger
import sys
import subprocess
import argparse
import time
import signal
import socket
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def find_free_port(start_port: int = 8501, max_attempts: int = 10) -> Optional[int]:
    """Найти свободный порт начиная с start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
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

        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "core/app.py",
            f"--server.port={port}",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ], check=True)
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


def run_reviews_parsing(limit_restaurants: Optional[int] = 50) -> None:
    """Парсинг отзывов с Яндекс.Карт"""
    logger.info("Парсинг отзывов...")

    try:
        result = fetch_reviews_for_all_restaurants(limit_restaurants=limit_restaurants)

        if result.get("success"):
            logger.success("Парсинг завершен")
            logger.info(f"Найдено отзывов: {result.get('total_reviews_found', 0)}")
            logger.info(f"Новых отзывов: {result.get('total_new_reviews', 0)}")
        else:
            logger.error(f"Ошибка парсинга: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Ошибка: {e}")


def run_nlp_processing() -> None:
    """NLP обработка отзывов"""
    logger.info("NLP обработка отзывов...")
    
    try:
        manager = get_job_manager()
        result = manager.run_job_now('nlp_processing')
        
        if result.get("success"):
            logger.success("NLP обработка завершена")
        else:
            logger.error(f"Ошибка NLP обработки: {result.get('error', 'Неизвестная ошибка')}")
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")


def run_initial_full_cycle() -> None:
    """Запускает полный первоначальный цикл для всех ресторанов"""
    logger.info("Запуск полного первоначального цикла...")
    logger.info("Обрабатываются ВСЕ рестораны без ограничений")
    
    try:
        # Этап 1: Синхронизация с Notion
        logger.info("\n" + "="*60)
        logger.info("ЭТАП 1/4: Синхронизация с Notion")
        logger.info("="*60)
        run_notion_sync()
        
        # Этап 2: Парсинг отзывов для ВСЕХ ресторанов
        logger.info("\n" + "="*60)
        logger.info("ЭТАП 2/4: Парсинг отзывов для всех ресторанов")
        logger.info("="*60)
        run_reviews_parsing(limit_restaurants=None)  # Без лимита
        
        # Этап 3: NLP обработка
        logger.info("\n" + "="*60)
        logger.info("ЭТАП 3/4: NLP обработка отзывов")
        logger.info("="*60)
        run_nlp_processing()
        
        # Этап 4: Запуск планировщика для регулярных задач
        logger.info("\n" + "="*60)
        logger.info("ЭТАП 4/4: Запуск планировщика для регулярных задач")
        logger.info("="*60)
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

        def signal_handler(signum, frame):
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
        if 'manager' in locals():
            manager.stop()


def run_full() -> None:
    """Запускает полный цикл: Scheduler + Notion -> UI -> Reviews (в фоне)"""
    logger.info("Запуск полного цикла...")

    try:
        # Запускаем планировщик в фоне
        logger.info("Запуск планировщика в фоновом режиме...")
        scheduler_process = subprocess.Popen([
            sys.executable, __file__, "--scheduler"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Планировщик запущен в фоне")

        logger.info("Этап 1/3: Синхронизация с Notion")
        run_notion_sync()

        logger.info("Этап 2/3: Запуск фонового парсинга отзывов...")
        subprocess.Popen([
            sys.executable, __file__, "--reviews"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Парсинг запущен в фоне")

        logger.info("Этап 3/3: Запуск веб-интерфейса")
        logger.info("Планировщик и парсинг работают в фоновом режиме")
        run_ui()

    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
        if 'scheduler_process' in locals():
            scheduler_process.terminate()
    except Exception as e:
        logger.error(f"Ошибка в полном цикле: {e}")
        if 'scheduler_process' in locals():
            scheduler_process.terminate()


def main() -> None:
    """Главная функция"""
    parser = argparse.ArgumentParser(description="RestoMaps Analytics")
    parser.add_argument("--ui", action="store_true", help="Запустить веб-интерфейс")
    parser.add_argument("--init-db", action="store_true", help="Инициализировать базу данных")
    parser.add_argument("--notion", action="store_true", help="Синхронизировать с Notion")
    parser.add_argument("--reviews", action="store_true", help="Парсить отзывы")
    parser.add_argument("--scheduler", action="store_true", help="Запустить планировщик задач")
    parser.add_argument("--full", action="store_true", help="Полный цикл: Scheduler + Notion + Reviews + UI")
    parser.add_argument("--initial", action="store_true", help="Полный первоначальный прогон для всех ресторанов + планировщик")

    args = parser.parse_args()

    logger.info("RestoMaps Analytics")

    if args.initial:
        run_initial_full_cycle()
    elif args.full:
        run_full()
    elif args.scheduler:
        run_scheduler()
    elif args.init_db:
        run_init_db()
    elif args.ui:
        run_ui()
    elif args.notion:
        run_notion_sync()
    elif args.reviews:
        run_reviews_parsing()
    else:
        run_ui()


if __name__ == "__main__":
    main()

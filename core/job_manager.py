import signal
import sys
import time
from typing import Any

from core.scheduler import Scheduler
from jobs.nlp_processing_job import NLPProcessingJob
from jobs.notion_sync_job import NotionSyncJob
from jobs.reviews_parsing_job import ReviewsParsingJob
from logger import get_logger

logger = get_logger(__name__)


class JobManager:
    """Менеджер джобов"""

    def __init__(self):
        self.scheduler = Scheduler()
        self.jobs = {}
        self._init_jobs()

    def _init_jobs(self):
        """Инициализация джобов"""
        self.jobs = {
            "notion_sync": NotionSyncJob(),
            "reviews_parsing": ReviewsParsingJob(batch_size=10, max_reviews=100),
            "nlp_processing": NLPProcessingJob(batch_size=50, force_reprocess=False),
        }
        logger.info(f"Инициализировано джобов: {len(self.jobs)}")

    def start(self):
        """Запустить менеджер и планировщик"""
        self._setup_scheduled_jobs()
        self.scheduler.start()
        logger.success("JobManager запущен")

    def stop(self):
        """Остановить менеджер"""
        self.scheduler.stop()
        logger.info("JobManager остановлен")

    def _setup_scheduled_jobs(self):
        """Настроить запланированные джобы"""
        # Синхронизация с Notion - каждый день в 06:00
        self.scheduler.add_job(
            func=self.run_job,
            trigger="cron",
            hour=6,
            minute=0,
            args=["notion_sync"],
            id="notion_sync_scheduled",
            name="Синхронизация с Notion",
            replace_existing=True,
        )

        # Парсинг отзывов - каждый день в 08:00
        self.scheduler.add_job(
            func=self.run_job,
            trigger="cron",
            hour=8,
            minute=0,
            args=["reviews_parsing"],
            id="reviews_parsing_scheduled",
            name="Парсинг отзывов",
            replace_existing=True,
        )

        # NLP обработка - каждый день в 09:00 (после парсинга)
        self.scheduler.add_job(
            func=self.run_job,
            trigger="cron",
            hour=9,
            minute=0,
            args=["nlp_processing"],
            id="nlp_processing_scheduled",
            name="NLP обработка",
            replace_existing=True,
        )

        logger.info("Запланированные джобы настроены")

    def run_job(self, job_name: str) -> dict[str, Any]:
        """Запустить джоб"""
        if job_name not in self.jobs:
            error_msg = f"Джоб '{job_name}' не найден"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        job = self.jobs[job_name]
        return job.run()

    def run_job_now(self, job_name: str) -> dict[str, Any]:
        """Запустить джоб немедленно"""
        logger.info(f"Немедленный запуск джоба: {job_name}")
        return self.run_job(job_name)

    def get_scheduler_status(self) -> dict[str, Any]:
        """Получить статус планировщика"""
        return self.scheduler.get_status()


# Глобальный экземпляр менеджера
_job_manager = None


def get_job_manager() -> JobManager:
    """Получить глобальный экземпляр менеджера джобов"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


def main():
    """Основная функция для запуска менеджера"""

    def signal_handler(signum, _frame):
        logger.info(f"Получен сигнал {signum}, останавливаем менеджер...")
        manager.stop()
        sys.exit(0)

    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    manager = get_job_manager()

    try:
        manager.start()
        logger.success("JobManager запущен! Нажмите Ctrl+C для остановки.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, останавливаем менеджер...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        manager.stop()


if __name__ == "__main__":
    main()

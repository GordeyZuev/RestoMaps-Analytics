from typing import Any

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from logger import get_logger

logger = get_logger(__name__)


class Scheduler:
    """Планировщик задач"""

    def __init__(self) -> None:
        self.scheduler = None
        self.running = False
        self._init_scheduler()

    def _init_scheduler(self) -> None:
        """Инициализация планировщика"""
        jobstores = {"default": MemoryJobStore()}

        executors = {"default": ThreadPoolExecutor(max_workers=4)}

        job_defaults = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 300}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="Europe/Moscow",
        )

        logger.info("Планировщик инициализирован")

    def start(self) -> None:
        """Запустить планировщик"""
        if self.running:
            logger.warning("Планировщик уже запущен")
            return

        self.scheduler.start()
        self.running = True
        logger.success("Планировщик запущен")

    def stop(self) -> None:
        """Остановить планировщик"""
        if not self.running:
            logger.warning("Планировщик не запущен")
            return

        self.scheduler.shutdown(wait=True)
        self.running = False
        logger.info("Планировщик остановлен")

    def add_job(self, func, trigger, **kwargs) -> None:
        """Добавить задачу"""
        self.scheduler.add_job(func, trigger, **kwargs)
        logger.info(f"Задача добавлена: {kwargs.get('id', 'unknown')}")

    def get_jobs(self) -> list:
        """Получить список задач"""
        return self.scheduler.get_jobs()

    def get_status(self) -> dict[str, Any]:
        """Получить статус планировщика"""
        jobs = self.get_jobs()
        return {
            "running": self.running,
            "jobs_count": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                }
                for job in jobs
            ],
        }

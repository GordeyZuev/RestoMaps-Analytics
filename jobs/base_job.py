from abc import ABC, abstractmethod
from typing import Dict, Any
from logger import get_logger


class BaseJob(ABC):
    """Базовый класс для всех джобов"""

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"job.{name}")

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """Выполнить джоб"""
        pass

    def run(self) -> Dict[str, Any]:
        """Запустить джоб с обработкой ошибок"""
        self.logger.info(f"Запуск джоба: {self.name}")

        try:
            result = self.execute()
            self.logger.success(f"Джоб {self.name} выполнен успешно")
            return {
                "success": True,
                "job_name": self.name,
                "result": result
            }
        except Exception as e:
            self.logger.error(f"Ошибка в джобе {self.name}: {e}")
            return {
                "success": False,
                "job_name": self.name,
                "error": str(e)
            }

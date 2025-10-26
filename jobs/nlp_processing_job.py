from typing import Any

from jobs.base_job import BaseJob
from parsers.nlp_processor import process_all_reviews_nlp


class NLPProcessingJob(BaseJob):
    """Джоб NLP обработки отзывов"""

    def __init__(self, batch_size: int = 50, force_reprocess: bool = False):
        super().__init__("nlp_processing")
        self.batch_size = batch_size
        self.force_reprocess = force_reprocess

    def execute(self) -> dict[str, Any]:
        """Выполнить NLP обработку"""
        self.logger.info(f"Начинаем NLP обработку отзывов (батч: {self.batch_size})...")

        process_all_reviews_nlp(
            force_reprocess=self.force_reprocess, batch_size=self.batch_size
        )

        self.logger.success("NLP обработка завершена")

        return {
            "processed": True,
            "batch_size": self.batch_size,
            "force_reprocess": self.force_reprocess,
        }

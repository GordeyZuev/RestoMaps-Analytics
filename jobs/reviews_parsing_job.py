from typing import Dict, Any
from jobs.base_job import BaseJob
from parsers.ya_maps_reviews_parser import fetch_reviews_for_all_restaurants


class ReviewsParsingJob(BaseJob):
    """Джоб парсинга отзывов"""

    def __init__(self, batch_size: int = 10, max_reviews: int = 100):
        super().__init__("reviews_parsing")
        self.batch_size = batch_size
        self.max_reviews = max_reviews

    def execute(self) -> Dict[str, Any]:
        """Выполнить парсинг отзывов"""
        self.logger.info(f"Начинаем парсинг отзывов (пачки по {self.batch_size})...")

        result = fetch_reviews_for_all_restaurants(
            max_reviews=self.max_reviews,
            scroll_attempts=5
        )

        self.logger.info(f"Парсинг завершен: {result}")

        return result

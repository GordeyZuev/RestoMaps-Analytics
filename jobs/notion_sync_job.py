from typing import Dict, Any
from jobs.base_job import BaseJob
from parsers.notion_data import sync_notion_data


class NotionSyncJob(BaseJob):
    """Джоб синхронизации с Notion"""

    def __init__(self):
        super().__init__("notion_sync")

    def execute(self) -> Dict[str, Any]:
        """Выполнить синхронизацию с Notion"""
        self.logger.info("Начинаем синхронизацию с Notion...")

        result = sync_notion_data()

        self.logger.info(f"Синхронизация завершена: {result['sync_results']}")

        return {
            "sync_results": result["sync_results"],
            "summary": result["summary"],
            "timestamp": result["timestamp"]
        }

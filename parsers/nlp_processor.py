
from database.database_manager import (
    process_all_reviews,
    process_restaurant_reviews,
    get_nlp_statistics
)
import argparse


def process_all_reviews_nlp(force_reprocess: bool = False, batch_size: int = 100):
    """Обработать все отзывы с помощью NLP анализа"""
    process_all_reviews(force_reprocess=force_reprocess, batch_size=batch_size)
    get_nlp_statistics()


def process_restaurant_reviews_nlp(restaurant_id: int, force_reprocess: bool = False, batch_size: int = 100):
    """Обработать отзывы конкретного ресторана с помощью NLP анализа"""
    process_restaurant_reviews(
        restaurant_id=restaurant_id,
        force_reprocess=force_reprocess,
        batch_size=batch_size
    )
    get_nlp_statistics()


def get_nlp_stats():
    """Получить статистику NLP обработки"""
    return get_nlp_statistics()


def main():
    parser = argparse.ArgumentParser(description='NLP процессор для обработки отзывов')
    parser.add_argument('--force', action='store_true', help='Переобработать все отзывы')
    parser.add_argument('--batch-size', type=int, default=100, help='Размер батча')
    parser.add_argument('--restaurant-id', type=int, help='ID ресторана для обработки')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')

    args = parser.parse_args()

    if args.stats:
        get_nlp_stats()
    elif args.restaurant_id:
        process_restaurant_reviews_nlp(
            restaurant_id=args.restaurant_id,
            force_reprocess=args.force,
            batch_size=args.batch_size
        )
    else:
        process_all_reviews_nlp(
            force_reprocess=args.force,
            batch_size=args.batch_size
        )


if __name__ == "__main__":
    main()

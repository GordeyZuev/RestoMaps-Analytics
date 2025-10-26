from sqlalchemy import and_, text

from database.database import SessionLocal
from database.models import Review
from logger import logger
from parsers.nlp_analyzer import ReviewProcessor


def process_review_nlp(db, review_id: int, processor: ReviewProcessor) -> Review | None:
    review = db.query(Review).filter(Review.id == review_id).first()

    if not review or not review.comment_text:
        return None

    try:
        result = processor.process_review(
            text=review.comment_text, rating=review.rating
        )

        review.processed_verdict = result["processed_verdict"]
        review.processed_tags = result["processed_tags"]
        review.sentiment_score = result["sentiment_score"]

        return review
    except Exception as e:
        logger.error(f"Ошибка при обработке отзыва {review_id}: {e}")
        return None


def process_restaurant_reviews(
    restaurant_id: int, force_reprocess: bool = False, batch_size: int = 100
) -> int:
    """Обрабатывает все отзывы ресторана"""
    db = SessionLocal()
    processor = ReviewProcessor()

    try:
        query = db.query(Review).filter(
            and_(Review.restaurant_id == restaurant_id, Review.comment_text.isnot(None))
        )

        if not force_reprocess:
            query = query.filter(Review.processed_verdict.is_(None))

        reviews = query.all()
        total = len(reviews)

        if total == 0:
            logger.info(f"Нет отзывов для обработки в ресторане {restaurant_id}")
            return 0

        logger.info(f"Обработка {total} отзывов ресторана {restaurant_id}")

        processed = 0
        for i, review in enumerate(reviews, 1):
            if process_review_nlp(db, review.id, processor):
                processed += 1

            if i % batch_size == 0:
                db.commit()
                logger.info(f"Обработано {i}/{total} отзывов")

        db.commit()
        logger.success(
            f"Обработано {processed}/{total} отзывов ресторана {restaurant_id}"
        )
        return processed

    finally:
        db.close()


def process_all_reviews(
    force_reprocess: bool = False, batch_size: int = 100
) -> dict[str, int]:
    db = SessionLocal()
    processor = ReviewProcessor()

    try:
        query = db.query(Review).filter(Review.comment_text.isnot(None))

        if not force_reprocess:
            query = query.filter(Review.processed_verdict.is_(None))

        reviews = query.all()
        total_reviews = len(reviews)

        if total_reviews == 0:
            logger.info("Нет отзывов для обработки")
            return {"total": 0, "processed": 0, "errors": 0}

        logger.info(f"Начало обработки {total_reviews} отзывов")

        processed_count = 0
        error_count = 0

        for i, review in enumerate(reviews, 1):
            if process_review_nlp(db, review.id, processor):
                processed_count += 1
            else:
                error_count += 1

            if i % batch_size == 0:
                db.commit()
                logger.info(
                    f"Прогресс: {i}/{total_reviews} "
                    f"({processed_count} успешно, {error_count} ошибок)"
                )

        db.commit()
        logger.success(
            f"✓ Обработка завершена: {processed_count} успешно, "
            f"{error_count} ошибок из {total_reviews}"
        )

        return {
            "total": total_reviews,
            "processed": processed_count,
            "errors": error_count,
        }

    finally:
        db.close()


def get_nlp_statistics():
    db = SessionLocal()

    try:
        total_reviews = db.query(Review).count()
        reviews_with_text = (
            db.query(Review).filter(Review.comment_text.isnot(None)).count()
        )
        processed_reviews = (
            db.query(Review).filter(Review.processed_verdict.isnot(None)).count()
        )

        logger.info("=" * 60)
        logger.info("СТАТИСТИКА NLP ОБРАБОТКИ")
        logger.info("=" * 60)
        logger.info(f"Всего отзывов в БД: {total_reviews}")
        logger.info(f"Отзывов с текстом: {reviews_with_text}")
        logger.info(f"Обработано NLP: {processed_reviews}")
        logger.info(f"Не обработано: {reviews_with_text - processed_reviews}")
        logger.info("=" * 60)

        if processed_reviews > 0:
            verdict_stats = db.execute(
                text("""
                SELECT processed_verdict, COUNT(*) as count
                FROM reviews
                WHERE processed_verdict IS NOT NULL
                GROUP BY processed_verdict
                ORDER BY count DESC
            """)
            ).fetchall()

            logger.info("\nРаспределение по вердиктам:")
            for verdict, count in verdict_stats:
                logger.info(f"  {verdict}: {count}")

    finally:
        db.close()

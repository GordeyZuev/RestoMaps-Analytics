from sqlalchemy.orm import Session
from sqlalchemy import and_
from .models import Restaurant, Review
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from logger import logger


def create_restaurant(db: Session, notion_id: str, name: str, place_type: str = None,
                      city: str = None, yandex_maps_url: str = None,
                      address: str = None, latitude: float = None,
                      longitude: float = None, yandex_rating: float = None,
                      tags: List[str] = None) -> Restaurant:
    db_restaurant = Restaurant(
        notion_id=notion_id,
        name=name,
        place_type=place_type,
        city=city,
        yandex_maps_url=yandex_maps_url,
        address=address,
        latitude=latitude,
        longitude=longitude,
        yandex_rating=yandex_rating,
        tags=tags
    )
    logger.info(f'Создание ресторана: {name}')
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant


def get_restaurant_by_notion_id(db: Session, notion_id: str) -> Optional[Restaurant]:
    return db.query(Restaurant).filter(Restaurant.notion_id == notion_id).first()


def get_restaurant_by_id(db: Session, restaurant_id: int) -> Optional[Restaurant]:
    return db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()


def get_or_create_restaurant(db: Session, notion_id: str, name: str, **kwargs) -> Restaurant:
    restaurant = get_restaurant_by_notion_id(db, notion_id)
    if not restaurant:
        restaurant = create_restaurant(db, notion_id, name, **kwargs)
    return restaurant


def get_restaurants_by_city(db: Session, city: str) -> List[Restaurant]:
    return db.query(Restaurant).filter(Restaurant.city == city).all()




def create_review(db: Session, restaurant_id: int, yandex_review_id: str,
                  author_name: str, rating: int, comment_text: str,
                  original_date: datetime = None, processed_tags: List[str] = None) -> Review:
    db_review = Review(
        restaurant_id=restaurant_id,
        yandex_review_id=yandex_review_id,
        author_name=author_name,
        rating=rating,
        comment_text=comment_text,
        original_date=original_date,
        processed_tags=processed_tags
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def get_review_by_yandex_id(db: Session, restaurant_id: int, yandex_review_id: str) -> Optional[Review]:
    return db.query(Review).filter(
        and_(
            Review.restaurant_id == restaurant_id,
            Review.yandex_review_id == yandex_review_id
        )
    ).first()


def get_reviews_by_restaurant(db: Session, restaurant_id: int, skip: int = 0, limit: int = 100) -> List[Review]:
    return db.query(Review).filter(Review.restaurant_id == restaurant_id).offset(skip).limit(limit).all()


def get_reviews_stats(db: Session, restaurant_id: int) -> Dict[str, Any]:
    reviews = db.query(Review).filter(Review.restaurant_id == restaurant_id).all()

    if not reviews:
        return {
            "total_reviews": 0,
            "avg_rating": 0,
            "rating_distribution": {},
            "recent_reviews": 0
        }

    total_reviews = len(reviews)
    avg_rating = sum(r.rating for r in reviews) / total_reviews

    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = len([r for r in reviews if r.rating == i])

    thirty_days_ago = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    recent_reviews = len([r for r in reviews if r.original_date and r.original_date >= thirty_days_ago])

    return {
        "total_reviews": total_reviews,
        "avg_rating": round(avg_rating, 2),
        "rating_distribution": rating_distribution,
        "recent_reviews": recent_reviews
    }


def save_reviews_batch(db: Session, restaurant_id: int, reviews_data: List[Dict[str, Any]]) -> Dict[str, int]:
    logger.info(f"Сохранение {len(reviews_data)} отзывов для ресторана {restaurant_id}")
    reviews_found = len(reviews_data)
    reviews_new = 0

    for review_data in reviews_data:
        yandex_review_id = review_data.get('yandex_review_id')

        existing_review = get_review_by_yandex_id(db, restaurant_id, yandex_review_id)

        if not existing_review:
            original_date = None
            date_raw = review_data.get('date_iso')
            if date_raw and date_raw != "Дата не указана":
                try:
                    cleaned = str(date_raw).strip()
                    if cleaned.endswith('Z'):
                        cleaned = cleaned[:-1] + '+00:00'
                    try:
                        original_date = datetime.fromisoformat(cleaned)
                    except ValueError:
                        if '.' in cleaned:
                            base, tail = cleaned.split('.', 1)
                            tz_part = ''
                            if '+' in tail:
                                _, tz_part = tail.split('+', 1)
                                tz_part = '+' + tz_part
                            elif '-' in tail:
                                _, tz_part = tail.split('-', 1)
                                tz_part = '-' + tz_part
                            else:
                                pass
                            cleaned2 = base + tz_part
                            original_date = datetime.fromisoformat(cleaned2)
                        else:
                            raise
                except Exception:
                    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
                        try:
                            original_date = datetime.strptime(cleaned, fmt)
                            break
                        except Exception:
                            continue

            create_review(
                db=db,
                restaurant_id=restaurant_id,
                yandex_review_id=yandex_review_id,
                author_name=review_data['author'],
                rating=review_data['rating'],
                comment_text=review_data['text'],
                original_date=original_date
            )
            reviews_new += 1

    logger.success(f"Сохранено {reviews_new} новых отзывов из {reviews_found} найденных")
    return {
        "reviews_found": reviews_found,
        "reviews_new": reviews_new
    }


def update_restaurant_rating(db: Session, restaurant_id: int, yandex_rating: float) -> Restaurant:
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if restaurant:
        restaurant.yandex_rating = yandex_rating
        restaurant.last_updated = datetime.utcnow()
        db.commit()
        db.refresh(restaurant)
    return restaurant


def update_restaurant_link_status(db: Session, restaurant_id: int, status: str) -> Restaurant:
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if restaurant:
        restaurant.yandex_url_status = status
        restaurant.yandex_url_last_checked = datetime.now(timezone.utc)
        db.commit()
        db.refresh(restaurant)
    return restaurant


def mark_restaurant_visited(db: Session, restaurant_id: int,
                            service_rating: float = None, food_rating: float = None,
                            coffee_rating: float = None, interior_rating: float = None,
                            comment: str = None) -> Restaurant:
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if restaurant:
        restaurant.visited = True
        if service_rating is not None:
            restaurant.my_service_rating = service_rating
        if food_rating is not None:
            restaurant.my_food_rating = food_rating
        if coffee_rating is not None:
            restaurant.my_coffee_rating = coffee_rating
        if interior_rating is not None:
            restaurant.my_interior_rating = interior_rating
        if comment is not None:
            restaurant.my_comment = comment
        restaurant.last_updated = datetime.utcnow()
        db.commit()
        db.refresh(restaurant)
    return restaurant


def get_restaurants_summary(db: Session) -> Dict[str, Any]:
    total_restaurants = db.query(Restaurant).count()
    visited_restaurants = db.query(Restaurant).filter(Restaurant.visited).count()

    cities = db.query(Restaurant.city).distinct().all()
    city_stats = {}
    for city in cities:
        if city[0]:
            count = db.query(Restaurant).filter(Restaurant.city == city[0]).count()
            city_stats[city[0]] = count

    return {
        "total_restaurants": total_restaurants,
        "visited_restaurants": visited_restaurants,
        "city_stats": city_stats
    }




def delete_restaurants_not_in_notion(db: Session, active_notion_ids: List[str]) -> Dict[str, Any]:
    try:
        query = db.query(Restaurant)
        if active_notion_ids is not None:
            query = query.filter(~Restaurant.notion_id.in_(active_notion_ids))
        to_delete = query.all()
        deleted = 0
        deleted_names: List[str] = []
        for r in to_delete:
            deleted_names.append(r.name)
            db.delete(r)
            deleted += 1
        if deleted:
            db.commit()
        return {"deleted": deleted, "names": deleted_names}
    except Exception as e:
        logger.error(f"Ошибка при удалении ресторанов, отсутствующих в Notion: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        raise

from typing import Dict, List, Any, Optional
import asyncio
from notion_client import Client
import os
from dotenv import load_dotenv
from database.database import SessionLocal, init_db
from database.crud import (
    get_or_create_restaurant,
    mark_restaurant_visited,
    get_restaurant_by_notion_id,
    get_restaurants_summary,
    delete_restaurants_not_in_notion
)
from database.models import Restaurant
from datetime import datetime, timezone
from logger import get_logger

from scripts.services import get_coord_by_address

logger = get_logger(__name__)

load_dotenv('config/.env')
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')


class NotionDataProcessor:
    def __init__(self):
        self.notion = Client(auth=NOTION_API_KEY)
        self.db = SessionLocal()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def get_notion_data(self) -> Dict[str, Any]:
        try:
            all_results = []
            has_more = True
            start_cursor = None

            while has_more:
                query_params = {
                    'database_id': NOTION_DATABASE_ID,
                    'page_size': 100
                }

                if start_cursor:
                    query_params['start_cursor'] = start_cursor

                response = self.notion.databases.query(**query_params)
                logger.info(f"🔍 Получен ответ от Notion API: {len(response.get('results', []))} записей")
                all_results.extend(response.get('results', []))

                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')

            return {
                'results': all_results,
                'has_more': False,
                'next_cursor': None
            }

        except Exception as e:
            logger.error(f"Ошибка при получении данных из Notion: {e}")
            raise

    def parse_notion_data(self, notion_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        restaurants = []

        for page in notion_data.get('results', []):
            properties = page.get('properties', {})

            restaurant = {
                'notion_id': page.get('id'),
                'name': self._extract_title(properties),
                'place_type': self._extract_place_type(properties),
                'city': self._extract_city(properties),
                'yandex_maps_url': self._extract_yandex_maps_url(properties),
                'visited': self._extract_visited_status(properties),
                'my_service_rating': self._extract_rating(properties, 'Сервис'),
                'my_food_rating': self._extract_rating(properties, 'Еда'),
                'my_coffee_rating': self._extract_rating(properties, 'Кофе'),
                'my_interior_rating': self._extract_rating(properties, 'Интерьер'),
                'tags': self._extract_tags(properties),
                'my_comment': self._extract_comment(properties),
                'address': self._extract_address(properties),
                'latitude': None,
                'longitude': None
            }

            restaurants.append(restaurant)

        return restaurants

    def save_to_database(self, restaurants_data: List[Dict[str, Any]]) -> Dict[str, int]:
        created_count = 0
        updated_count = 0

        for restaurant_data in restaurants_data:
            try:
                existing_restaurant = get_restaurant_by_notion_id(
                    self.db,
                    restaurant_data['notion_id']
                )

                if existing_restaurant:
                    if self._update_restaurant(existing_restaurant, restaurant_data):
                        updated_count += 1
                else:
                    self._create_restaurant(restaurant_data)
                    created_count += 1

            except Exception as e:
                logger.error(f"Ошибка при сохранении ресторана {restaurant_data.get('name', 'Unknown')}: {e}")
                try:
                    self.db.rollback()
                except BaseException:
                    pass
                continue

        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Ошибка при коммите транзакции: {e}")
            try:
                self.db.rollback()
            except BaseException:
                pass
            raise

        return {
            "created": created_count,
            "updated": updated_count,
            "total_processed": len(restaurants_data)
        }

    def _create_restaurant(self, restaurant_data: Dict[str, Any]) -> Restaurant:
        logger.info(f"Создание нового ресторана: {restaurant_data['name']}")

        try:
            if restaurant_data['address']:
                logger.info(f"Получение координат для адреса: {restaurant_data['address']}")
                coords = _get_coords_sync(restaurant_data['address'])
                if coords:
                    restaurant_data['latitude'] = coords.get('latitude')
                    restaurant_data['longitude'] = coords.get('longitude')
                    if coords.get('full_address'):
                        restaurant_data['address'] = coords['full_address']
                    logger.success(
                        f"Координаты получены: {restaurant_data['latitude']}, {restaurant_data['longitude']}")
                else:
                    logger.warning(f"Не удалось получить координаты для: {restaurant_data['address']}")
            else:
                logger.warning(f"Адрес не указан для: {restaurant_data['name']}")
        except Exception as e:
            logger.error(f"Ошибка при геокодировании адреса {restaurant_data['address']}: {e}")

        restaurant = get_or_create_restaurant(
            db=self.db,
            notion_id=restaurant_data['notion_id'],
            name=restaurant_data['name'],
            place_type=restaurant_data['place_type'],
            city=restaurant_data['city'],
            yandex_maps_url=(restaurant_data['yandex_maps_url'] or None),
            address=restaurant_data['address'],
            tags=restaurant_data['tags'],
            latitude=restaurant_data['latitude'],
            longitude=restaurant_data['longitude']
        )

        if restaurant_data['visited']:
            mark_restaurant_visited(
                db=self.db,
                restaurant_id=restaurant.id,
                service_rating=restaurant_data['my_service_rating'],
                food_rating=restaurant_data['my_food_rating'],
                coffee_rating=restaurant_data['my_coffee_rating'],
                interior_rating=restaurant_data['my_interior_rating'],
                comment=restaurant_data['my_comment']
            )

        return restaurant

    def _update_restaurant(self, restaurant: Restaurant, restaurant_data: Dict[str, Any]) -> bool:
        changed = False

        def assign_if_changed(field_name: str, new_value: Any):
            nonlocal changed
            if getattr(restaurant, field_name) != new_value:
                setattr(restaurant, field_name, new_value)
                changed = True

        assign_if_changed('name', restaurant_data['name'])
        assign_if_changed('place_type', restaurant_data['place_type'])
        assign_if_changed('city', restaurant_data['city'])
        if restaurant_data['yandex_maps_url']:
            if restaurant.yandex_maps_url != restaurant_data['yandex_maps_url']:
                assign_if_changed('yandex_maps_url', restaurant_data['yandex_maps_url'])
        else:
            if restaurant.yandex_url_status != 'unknown':
                assign_if_changed('yandex_url_status', 'unknown')
        assign_if_changed('address', restaurant_data['address'])
        assign_if_changed('tags', restaurant_data['tags'])

        if restaurant_data['visited']:
            assign_if_changed('visited', True)
            assign_if_changed('my_service_rating', restaurant_data['my_service_rating'])
            assign_if_changed('my_food_rating', restaurant_data['my_food_rating'])
            assign_if_changed('my_coffee_rating', restaurant_data['my_coffee_rating'])
            assign_if_changed('my_interior_rating', restaurant_data['my_interior_rating'])
            assign_if_changed('my_comment', restaurant_data['my_comment'])

        if changed:
            restaurant.last_updated = datetime.now(timezone.utc)

        return changed

    def sync_notion_to_database(self) -> Dict[str, Any]:
        try:
            notion_data = self.get_notion_data()
            restaurants_data = self.parse_notion_data(notion_data)

            sync_results = self.save_to_database(restaurants_data)

            active_notion_ids = [r['notion_id'] for r in restaurants_data]
            deletion_result = delete_restaurants_not_in_notion(self.db, active_notion_ids)
            summary = get_restaurants_summary(self.db)

            return {
                "sync_results": {
                    **sync_results,
                    "deleted": deletion_result.get("deleted", 0)
                },
                "summary": summary,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Ошибка при синхронизации: {e}")
            raise

    def _extract_title(self, properties: Dict[str, Any]) -> str:
        title_prop = properties.get('Место', {}).get('title', [])
        if title_prop:
            return title_prop[0].get('text', {}).get('content', '').strip()
        return ''

    def _extract_place_type(self, properties: Dict[str, Any]) -> str:
        type_mapping = {
            'Ресторан': 'restaurant',
            'Кафе': 'cafe',
            'Бар': 'bar',
            'Пекарня': 'bakery'
        }

        type_prop = properties.get('Тип', {}).get('multi_select', [])
        if type_prop:
            russian_type = type_prop[0].get('name', '')
            return type_mapping.get(russian_type, 'other')
        return 'other'

    def _extract_city(self, properties: Dict[str, Any]) -> str:
        city_prop = properties.get('Город', {}).get('multi_select', [])
        if city_prop:
            return city_prop[0].get('name', '')
        return ''

    def _extract_yandex_maps_url(self, properties: Dict[str, Any]) -> str:
        url_manual_prop = properties.get('URL Manual', {})
        if url_manual_prop.get('type') == 'url':
            url_manual = url_manual_prop.get('url')
            if url_manual and url_manual.strip():
                return url_manual.strip()
        return ''

    def _extract_visited_status(self, properties: Dict[str, Any]) -> bool:
        status_prop = properties.get('Посещено', {}).get('status', {})
        return status_prop.get('name') == 'Был' if status_prop else False

    def _extract_rating(self, properties: Dict[str, Any], rating_name: str) -> Optional[float]:
        rating_prop = properties.get(rating_name, {}).get('number')
        return float(rating_prop) if rating_prop is not None else None

    def _extract_tags(self, properties: Dict[str, Any]) -> List[str]:
        tags_prop = properties.get('Ярлычки', {}).get('multi_select', [])
        return [tag.get('name') for tag in tags_prop if tag.get('name')]

    def _extract_comment(self, properties: Dict[str, Any]) -> str:
        comment_prop = properties.get('Комментарий', {}).get('rich_text', [])
        comment_parts = []

        for text_item in comment_prop:
            content = text_item.get('text', {}).get('content', '')
            if content.strip():
                comment_parts.append(content.strip())

        return '\n'.join(comment_parts)

    def _extract_address(self, properties: Dict[str, Any]) -> str:
        address_prop = properties.get('Адрес', {}).get('rich_text', [])
        if address_prop:
            return address_prop[0].get('text', {}).get('content', '')
        return ''


def _get_coords_sync(address: str) -> Optional[Dict[str, Any]]:
    if not address or not address.strip():
        return None
    try:
        return asyncio.run(get_coord_by_address(address))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(get_coord_by_address(address))
        finally:
            loop.close()
    except Exception:
        return None


def sync_notion_data():
    init_db()

    with NotionDataProcessor() as processor:
        return processor.sync_notion_to_database()


if __name__ == "__main__":
    try:
        result = sync_notion_data()
        logger.success("Синхронизация завершена успешно")
        logger.info(f"Результаты: {result['sync_results']}")
        logger.info(f"Сводка: {result['summary']}")
    except Exception:
        logger.exception("Ошибка при синхронизации")

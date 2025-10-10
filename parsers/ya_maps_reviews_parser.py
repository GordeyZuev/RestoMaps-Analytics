import os
import time
import re
import asyncio
from typing import List, Dict, Optional, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

from bs4 import BeautifulSoup

import httpx

from dotenv import load_dotenv
from logger import logger

from database.database import SessionLocal, init_db
from database.models import Restaurant
from database.crud import (
    get_restaurant_by_notion_id,
    save_reviews_batch,
    update_restaurant_rating,
    get_reviews_stats,
    update_restaurant_link_status
)

load_dotenv('config/.env')

YA_GEO_SUGEST_API_KEY = os.getenv("YA_GEO_SUGEST_API_KEY")

BROWSER_OPTIONS = {
    "headless": "--headless=new",
    "no_sandbox": "--no-sandbox",
    "disable_dev_shm": "--disable-dev-shm-usage",
    "window_size": "--window-size=1920,1080",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DEFAULT_SCROLL_ATTEMPTS = 5
DEFAULT_MAX_REVIEWS = 100
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))
ELEMENT_WAIT_TIMEOUT = int(os.getenv("ELEMENT_WAIT_TIMEOUT", "20"))
SCROLL_DELAY = int(os.getenv("SCROLL_DELAY", "2"))
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "2"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))


def setup_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()

    for option in BROWSER_OPTIONS.values():
        options.add_argument(option)

    # Явно указываем бинарь Chromium внутри контейнера
    chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin

    # Используем Selenium Manager (встроен в selenium 4.x) для подбора совместимого драйвера
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    return driver


def extract_review_data(review_element: BeautifulSoup) -> Optional[Dict[str, Any]]:
    try:
        author = _extract_author_name(review_element)
        user_id = _extract_user_id(review_element)
        rating = _extract_rating(review_element)
        text = _extract_review_text(review_element)
        date_iso = _extract_review_date(review_element)

        if user_id:
            yandex_review_id = user_id if len(user_id) > 7 else f"{user_id}_{date_iso[:10]}"
        else:
            yandex_review_id = f"{author}_{date_iso[:10]}"

        return {
            'author': author,
            'yandex_review_id': yandex_review_id,
            'rating': rating,
            'text': text,
            'date_iso': date_iso
        }

    except Exception as e:
        logger.error(f"Ошибка при извлечении данных отзыва: {e}")
        return None


def _extract_author_name(review_element: BeautifulSoup) -> str:
    selectors = ['span[itemprop="name"]', 'div.business-review-view__author-name', 'span.business-review-view__author']
    for selector in selectors:
        elem = review_element.select_one(selector)
        if elem:
            return elem.get_text(strip=True)
    return "Аноним"


def _extract_user_id(review_element: BeautifulSoup) -> Optional[str]:
    # Из ссылки на профиль
    author_container = review_element.find('div', class_='business-review-view__author-container')
    if author_container:
        for link in author_container.find_all('a', href=True):
            if '/maps/user/' in link['href']:
                return link['href'].split('/maps/user/')[-1].split('/')[0]

    # Из аватара
    avatar_div = review_element.find('div', class_='user-icon-view__icon')
    if avatar_div and 'style' in avatar_div.attrs:
        style = avatar_div['style']
        if 'background-image' in style:
            url_match = re.search(r'url\("([^"]+)"\)', style)
            if url_match and 'get-yapic' in url_match.group(1):
                parts = url_match.group(1).split('/')
                if len(parts) >= 5:
                    return parts[4]
    return None


def _extract_rating(review_element: BeautifulSoup) -> int:
    rating_div = review_element.find('div', class_='business-rating-badge-view__stars')
    if rating_div and 'aria-label' in rating_div.attrs:
        try:
            return int(rating_div['aria-label'].split()[1])
        except (IndexError, ValueError):
            pass

    stars = review_element.find_all('span', class_='business-rating-badge-view__star _full')
    return len(stars)


def _extract_review_text(review_element: BeautifulSoup) -> str:
    selectors = ['span.spoiler-view__text-container', 'div.business-review-view__body']
    for selector in selectors:
        elem = review_element.select_one(selector)
        if elem:
            return elem.get_text(strip=True)
    return "Нет текста"


def _extract_review_date(review_element: BeautifulSoup) -> str:
    date_elem = review_element.find('span', class_='business-review-view__date')
    if date_elem:
        meta_date = date_elem.find('meta', itemprop='datePublished')
        if meta_date and 'content' in meta_date.attrs:
            return meta_date['content']
        return date_elem.get_text(strip=True)
    return "Дата не указана"


def parse_yandex_reviews(url: str, max_reviews: int = -
                         1, scroll_attempts: int = DEFAULT_SCROLL_ATTEMPTS) -> List[Dict[str, Any]]:
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        driver = None
        try:
            logger.info(f"Попытка {attempt}/{MAX_RETRY_ATTEMPTS}: парсинг отзывов")
            logger.info(f"URL: {url}")

            driver = setup_driver()
            driver.get(url)
            time.sleep(3)

            if not _verify_page_loaded(driver):
                raise Exception("Страница не загрузилась корректно")

            _sort_reviews_by_newest(driver)

            if not _wait_for_reviews_loading(driver):
                raise Exception("Отзывы не загрузились")

            _scroll_page_for_reviews(driver, scroll_attempts)
            reviews = _parse_reviews_from_page(driver, max_reviews)

            if reviews:
                logger.success(f"✓ Найдено отзывов: {len(reviews)}")
                return reviews
            else:
                logger.warning(f"⚠ Отзывы не найдены на попытке {attempt}")
                if attempt < MAX_RETRY_ATTEMPTS:
                    logger.info(f"Повторная попытка через {RETRY_DELAY} секунд...")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    logger.error("Исчерпаны все попытки, отзывы не найдены")
                    return []

        except Exception as e:
            logger.error(f"✗ Ошибка на попытке {attempt}/{MAX_RETRY_ATTEMPTS}: {e}")
            if attempt < MAX_RETRY_ATTEMPTS:
                logger.info(f"Повторная попытка через {RETRY_DELAY} секунд...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Исчерпаны все попытки")
                return []

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии драйвера: {e}")

    return []


def _sort_reviews_by_newest(driver: webdriver.Chrome) -> None:
    try:
        sort_selectors = [
            ".business-reviews-card-view__ranking .rating-ranking-view",
            ".rating-ranking-view",
            "[role='button'][aria-haspopup='true']"
        ]

        sort_btn = None
        for selector in sort_selectors:
            try:
                sort_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                break
            except BaseException:
                continue

        if not sort_btn:
            return

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_btn)
        time.sleep(1)
        try:
            sort_btn.click()
        except BaseException:
            driver.execute_script("arguments[0].click();", sort_btn)
        time.sleep(2)

        popup_selectors = [".rating-ranking-view__popup", ".popup", "[class*='popup']"]
        popup = None
        for selector in popup_selectors:
            try:
                popup = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                )
                break
            except BaseException:
                continue

        if popup:
            newest_selectors = [
                ".//div[text()='По новизне']",
                ".//span[text()='По новизне']",
                "[data-value='newest']"
            ]

            for selector in newest_selectors:
                try:
                    newest_item = popup.find_element(
                        By.XPATH if selector.startswith('.//') else By.CSS_SELECTOR, selector)
                    driver.execute_script("arguments[0].click();", newest_item)
                    time.sleep(3)
                    break
                except BaseException:
                    continue

    except Exception as e:
        logger.warning(f"Ошибка при сортировке отзывов: {e}")


def _verify_page_loaded(driver: webdriver.Chrome) -> bool:
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )

        if "404" in driver.title or "Ошибка" in driver.title:
            logger.error("Загружена страница ошибки")
            return False

        return True
    except Exception as e:
        logger.error(f"Страница не загрузилась: {e}")
        return False


def _wait_for_reviews_loading(driver: webdriver.Chrome) -> bool:
    try:
        selectors = [
            '.business-reviews-card-view__review',
            '[class*="business-review"]',
            '[class*="review-card"]'
        ]

        for selector in selectors:
            try:
                WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logger.info(f"✓ Отзывы загружены (селектор: {selector})")
                return True
            except BaseException:
                continue

        logger.warning("⚠ Не удалось найти отзывы ни по одному из селекторов")
        return False

    except Exception as e:
        logger.warning(f"⚠ Ошибка при ожидании загрузки отзывов: {e}")
        return False


def _scroll_page_for_reviews(driver: webdriver.Chrome, scroll_attempts: int) -> None:
    last_height = driver.execute_script("return document.body.scrollHeight")

    for attempt in range(scroll_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_DELAY)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def _parse_reviews_from_page(driver: webdriver.Chrome, max_reviews: int) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    review_elements = soup.find_all('div', class_='business-reviews-card-view__review')

    reviews = []
    for element in review_elements[:max_reviews]:
        review_data = extract_review_data(element)
        if review_data:
            reviews.append(review_data)

    return reviews


async def make_request(place: str, place_coordinates: Dict[str, Any]) -> Optional[str]:
    if not YA_GEO_SUGEST_API_KEY:
        logger.warning("YA_GEO_SUGEST_API_KEY не установлен")
        return None

    url = "https://suggest-maps.yandex.ru/v1/suggest"

    params = {
        "text": place,
        "print_address": 1,
        "types": "biz",
        "results": 1,
        "attrs": "uri",
        "apikey": YA_GEO_SUGEST_API_KEY
    }

    if (
        place_coordinates
        and place_coordinates.get('latitude') is not None
        and place_coordinates.get('longitude') is not None
    ):
        params["ll"] = f"{place_coordinates['latitude']},{place_coordinates['longitude']}"

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Поиск места: {place}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('results'):
                logger.success(f"Место найдено: {data['results'][0].get('title', 'Название не указано')}")
                place_info = data['results'][0]
                yandex_uri = place_info.get('uri')
                if not yandex_uri:
                    logger.error("В ответе API отсутствует uri")
                    return None
                search_link = f"https://yandex.ru/maps/?mode=poi&poi[uri]={yandex_uri}&tab=reviews"
                return search_link
            else:
                logger.error(f"Место не найдено: {place}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при запросе к API: {e}")
            return None


def parse_and_save_reviews(
    notion_id: str,
    max_reviews: int = DEFAULT_MAX_REVIEWS,
    scroll_attempts: int = DEFAULT_SCROLL_ATTEMPTS
) -> Dict[str, Any]:
    logger.info(f'Начинаем парсинг отзывов для notion_id: {notion_id}')
    init_db()
    db = SessionLocal()

    try:
        restaurant = get_restaurant_by_notion_id(db, notion_id)
        if not restaurant:
            return {"success": False, "error": "Ресторан с указанным notion_id не найден"}

        place_name = restaurant.name
        place_coordinates = {
            "latitude": restaurant.latitude,
            "longitude": restaurant.longitude
        }

        address_missing = (restaurant.address is None) or (str(restaurant.address).strip() == "")
        coords_missing = (place_coordinates["latitude"] is None) or (place_coordinates["longitude"] is None)
        if address_missing and coords_missing:
            logger.error("У места отсутствуют адрес и координаты")
            return {
                "success": False,
                "error": "У места отсутствуют адрес и координаты. Формирование ссылки невозможно."
            }

        if coords_missing:
            logger.warning("У места отсутствуют координаты. Поиск будет выполнен без параметра ll.")

        logger.info(f"Начинаем парсинг отзывов: {place_name}")

        if restaurant.yandex_maps_url and restaurant.yandex_url_status == 'ok':
            reviews_url = restaurant.yandex_maps_url
            logger.info(f"✓ Используем сохраненную URL из БД: {reviews_url}")
        else:
            logger.info(f"🔍 URL не найдена в БД, ищем через Яндекс API...")
            reviews_url = _build_reviews_url(place_name, place_coordinates)

            if not reviews_url:
                error_msg = "Не удалось сформировать ссылку на отзывы (место не найдено в Яндекс.Картах)"
                logger.error(error_msg)
                update_restaurant_link_status(db, restaurant.id, 'not_found')
                return {"success": False, "error": error_msg, "skip": True}

            restaurant.yandex_maps_url = reviews_url
            db.commit()
            logger.success(f"✓ URL найдена и сохранена в БД: {reviews_url}")

        reviews = parse_yandex_reviews(reviews_url, max_reviews, scroll_attempts)
        if not reviews:
            logger.warning(
                f"⚠ Отзывы не найдены для {place_name}. Возможно, у ресторана пока нет отзывов или возникла проблема с парсингом")
            update_restaurant_link_status(db, restaurant.id, 'broken')
            return {
                "success": True,  # Считаем это успехом, просто нет данных
                "restaurant_id": restaurant.id,
                "restaurant_name": place_name,
                "reviews_found": 0,
                "reviews_new": 0,
                "total_reviews": 0,
                "avg_rating": 0,
                "warning": "Отзывы не найдены"
            }

        logger.info(f"Найдено {len(reviews)} отзывов, сохраняем в базу")
        update_restaurant_link_status(db, restaurant.id, 'ok')
        save_result = _save_reviews_to_database(db, restaurant.id, reviews)
        _update_restaurant_statistics(db, restaurant.id, reviews)
        final_stats = _get_final_statistics(db, restaurant.id, place_name, save_result)

        logger.success(f"Парсинг завершен успешно для: {place_name}")
        return final_stats

    except Exception as e:
        error_msg = f"Ошибка при парсинге: {str(e)}"
        logger.error(error_msg)
        try:
            if 'restaurant' in locals() and restaurant:
                update_restaurant_link_status(db, restaurant.id, 'unreachable')
        except Exception:
            pass
        return {"success": False, "error": error_msg}

    finally:
        db.close()


def _build_reviews_url(place_name: str, place_coordinates: Dict[str, Any]) -> Optional[str]:
    try:
        logger.debug(f"place_name: {place_name}")
        return asyncio.run(make_request(place_name, place_coordinates))
    except Exception as e:
        logger.error(f"Ошибка при построении ссылки: {e}")
        return None


def _save_reviews_to_database(db: SessionLocal, restaurant_id: int, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    return save_reviews_batch(db, restaurant_id, reviews)


def _update_restaurant_statistics(db: SessionLocal, restaurant_id: int, reviews: List[Dict[str, Any]]) -> None:
    if reviews:
        avg_rating = sum(r['rating'] for r in reviews) / len(reviews)
        update_restaurant_rating(db, restaurant_id, avg_rating)


def _get_final_statistics(db: SessionLocal, restaurant_id: int, place_name: str,
                          save_result: Dict[str, Any]) -> Dict[str, Any]:
    stats = get_reviews_stats(db, restaurant_id)
    return {
        "success": True,
        "restaurant_id": restaurant_id,
        "restaurant_name": place_name,
        "reviews_found": save_result["reviews_found"],
        "reviews_new": save_result["reviews_new"],
        "total_reviews": stats['total_reviews'],
        "avg_rating": stats['avg_rating']
    }


def fetch_reviews_for_all_restaurants(
    max_reviews: int = DEFAULT_MAX_REVIEWS,
    scroll_attempts: int = DEFAULT_SCROLL_ATTEMPTS,
    limit_restaurants: int = None
) -> Dict[str, Any]:
    """Парсинг отзывов для ресторанов из БД"""
    init_db()
    db = SessionLocal()

    try:
        query = db.query(Restaurant).order_by(Restaurant.last_updated.desc())

        if limit_restaurants:
            query = query.limit(limit_restaurants)

        restaurants = query.all()
        total = len(restaurants)

        if total == 0:
            logger.warning("В БД нет ресторанов")
            return {"success": False, "error": "В БД нет ресторанов"}

        logger.info(f"Найдено {total} ресторанов в БД")
        if limit_restaurants:
            logger.info(f"Обрабатываем только {limit_restaurants} самых свежих ресторанов")
        logger.info(f"Начинаем получение отзывов...")

        success_count = 0
        error_count = 0
        warning_count = 0  # Рестораны без отзывов
        skipped_count = 0   # Рестораны, которые не удалось найти
        total_new_reviews = 0
        total_found_reviews = 0

        for i, restaurant in enumerate(restaurants, 1):
            logger.info(f"\n{'=' * 60}")
            logger.info(f"[{i}/{total}] Обработка: {restaurant.name}")
            logger.info(f"notion_id: {restaurant.notion_id}")
            logger.info(f"{'=' * 60}")

            try:
                result = parse_and_save_reviews(
                    notion_id=restaurant.notion_id,
                    max_reviews=max_reviews,
                    scroll_attempts=scroll_attempts
                )

                if result.get("success"):
                    reviews_new = result.get('reviews_new', 0)
                    reviews_found = result.get('reviews_found', 0)

                    if result.get('warning'):
                        # Нет отзывов, но парсинг прошёл
                        warning_count += 1
                        logger.warning(f"⚠ {restaurant.name}: {result.get('warning')}")
                    else:
                        # Успешно найдены отзывы
                        success_count += 1
                        total_new_reviews += reviews_new
                        total_found_reviews += reviews_found
                        logger.success(f"✓ {restaurant.name}: {reviews_new} новых отзывов из {reviews_found} найденных")
                else:
                    # Ошибка парсинга
                    if result.get('skip'):
                        skipped_count += 1
                        logger.warning(
                            f"⊘ {restaurant.name}: {result.get('error', 'Ресторан не найден в Яндекс.Картах')}")
                    else:
                        error_count += 1
                        logger.error(f"✗ {restaurant.name}: {result.get('error', 'Неизвестная ошибка')}")

            except Exception as e:
                error_count += 1
                logger.error(f"✗ {restaurant.name}: Критическая ошибка - {str(e)}")

        logger.info("\n" + "=" * 60)
        logger.success(f"ОБРАБОТКА ЗАВЕРШЕНА!")
        logger.info(f"✓ Успешно обработано: {success_count}/{total} ресторанов")
        logger.info(f"⚠ Без отзывов: {warning_count}/{total} ресторанов")
        logger.info(f"⊘ Пропущено (не найдено): {skipped_count}/{total} ресторанов")
        logger.info(f"✗ Ошибок: {error_count}/{total} ресторанов")
        logger.info(f"Всего найдено отзывов: {total_found_reviews}")
        logger.info(f"Новых отзывов добавлено: {total_new_reviews}")
        logger.info("=" * 60)

        return {
            "success": True,
            "total_restaurants": total,
            "processed_successfully": success_count,
            "no_reviews": warning_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total_reviews_found": total_found_reviews,
            "total_new_reviews": total_new_reviews
        }

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Парсинг отзывов из Яндекс.Карт')
    parser.add_argument('--all', action='store_true', help='Получить отзывы для всех ресторанов из БД')
    parser.add_argument('--notion-id', type=str, help='Notion ID конкретного ресторана')
    parser.add_argument('--max-reviews', type=int, default=DEFAULT_MAX_REVIEWS, help='Максимум отзывов на ресторан')
    parser.add_argument(
        '--scroll-attempts',
        type=int,
        default=DEFAULT_SCROLL_ATTEMPTS,
        help='Количество попыток прокрутки')
    parser.add_argument('--limit', type=int, help='Количество ресторанов для обработки (самые свежие)')

    args = parser.parse_args()

    if args.all:
        result = fetch_reviews_for_all_restaurants(
            max_reviews=args.max_reviews,
            scroll_attempts=args.scroll_attempts,
            limit_restaurants=args.limit
        )
        if result.get("success"):
            logger.success("Парсинг всех ресторанов завершен успешно!")
        else:
            logger.error(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")

    elif args.notion_id:
        result = parse_and_save_reviews(
            notion_id=args.notion_id,
            max_reviews=args.max_reviews,
            scroll_attempts=args.scroll_attempts
        )
        if result["success"]:
            logger.success("Парсинг завершен успешно!")
            logger.info(f"Статистика: {result['reviews_new']} новых отзывов из {result['reviews_found']} найденных")
            logger.info(f"Средний рейтинг: {result['avg_rating']:.1f}")
        else:
            logger.error(f"Ошибка при парсинге: {result['error']}")

    else:
        logger.info("\nПримеры использования:")
        logger.info("  python ya_maps_reviews_parser.py --all")
        logger.info("  python ya_maps_reviews_parser.py --all --limit 50  # только 50 самых свежих")
        logger.info("  python ya_maps_reviews_parser.py --notion-id 18e4fad2-f8ee-805d-8a7c-c34099c6d48f")
        logger.info("  python ya_maps_reviews_parser.py --all --max-reviews 50 --scroll-attempts 3")

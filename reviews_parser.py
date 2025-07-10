# Стандартная библиотека
import os
import time

# Сторонние библиотеки
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import httpx
import asyncio

# Загрузка переменных окружения
load_dotenv()
YA_GEO_SUGEST_API_KEY = os.getenv("YA_GEO_SUGEST_API_KEY")

def setup_driver():
    """Настройка веб-драйвера с автоматической установкой ChromeDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

def extract_review_data(review_element):
    """Извлечение данных из одного отзыва с проверкой всех полей"""
    try:
        # Автор
        author_elem = review_element.find('span', itemprop='name')
        if not author_elem:
            author_elem = review_element.find('div', class_='business-review-view__author-name')
        if not author_elem:
            author_elem = review_element.find('span', class_='business-review-view__author')
        author = author_elem.get_text(strip=True) if author_elem else "Аноним"
        
        # Рейтинг
        stars = review_element.find_all('span', class_='business-rating-badge-view__star _full')
        rating = len(stars)
        rating_div = review_element.find('div', class_='business-rating-badge-view__stars')
        if rating_div and 'aria-label' in rating_div.attrs:
            try:
                aria_rating = int(rating_div['aria-label'].split()[1])
                rating = aria_rating
            except (IndexError, ValueError):
                pass
        
        # Текст
        text_elem = review_element.find('span', class_='spoiler-view__text-container')
        if not text_elem:
            text_elem = review_element.find('div', class_='business-review-view__body')
        text = text_elem.get_text(strip=True) if text_elem else "Нет текста"
        
        # Дата
        date_elem = review_element.find('span', class_='business-review-view__date')
        date = date_elem.get_text(strip=True) if date_elem else "Дата не указана"
        
        return {
            'author': author,
            'rating': rating,
            'text': text,
            'date': date
        }
    except Exception as e:
        print(f"Ошибка при извлечении данных отзыва: {e}")
        return None

def parse_yandex_reviews(url, max_reviews=100, scroll_attempts=5):
    driver = setup_driver()
    try:
        driver.get(url)

        # --- Эмулируем нажатие на кнопку: Сортировка "По новизне" ---
        try:
            # 1) Найти и открыть меню сортировки
            sort_btn = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((
                    By.CSS_SELECTOR,
                    ".business-reviews-card-view__ranking .rating-ranking-view"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", sort_btn)
            driver.execute_script("arguments[0].click();", sort_btn)

            # 2) Дождаться выпадающего меню
            popup = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((
                    By.CSS_SELECTOR,
                    ".rating-ranking-view__popup"
                ))
            )

            # 3) Кликнуть на пункт "По новизне" в выпадающем меню
            newest_item = popup.find_element(
                By.XPATH,
                ".//div[text()='По новизне']"
            )
            driver.execute_script("arguments[0].click();", newest_item)

            # 4) Подождать, пока меню исчезнет и сортировка применится
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element(popup)
            )
        except Exception as e:
            print(f"Не удалось переключиться на «По новизне»: {e}")

        # Ждём
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.business-reviews-card-view__review'))
        )
        # Скроллим
        last_h = driver.execute_script("return document.body.scrollHeight")
        for _ in range(scroll_attempts):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_h = driver.execute_script("return document.body.scrollHeight")
            if new_h == last_h:
                break
            last_h = new_h

        # Парсим отзывы
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        elems = soup.find_all('div', class_='business-reviews-card-view__review')

        reviews = []
        for el in elems[:max_reviews]:
            data = extract_review_data(el)
            if data:
                reviews.append(data)

        return reviews

    finally:
        driver.quit()


async def make_request(place):
    """Достаем URI Места в Яндекс Картах по названию (Yandex Geosuggest API)"""

    url = "https://suggest-maps.yandex.ru/v1/suggest"
    
    params = {
        "text": place, # Название Места
        "print_address": 1, # Вывод одного адреса
        "types": "biz", # Только бизнес-объекты
        "results": 1, # Количество результатов
        "attrs": "uri", # Вывод URI места
        "apikey": YA_GEO_SUGEST_API_KEY # API Key
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None


if __name__ == "__main__":

    reviews_number = 5
    place_name = 'Кафе Салют Москва'
    result = asyncio.run(make_request(place_name))
    # print(f"Результат запроса: {result}")

    # Ссылка на раздел с отзывами на место.
    search_link = 'https://yandex.ru/maps/?mode=poi&poi[uri]=' + result['results'][0]['uri'] + '&tab=reviews' # Ссылка на отзывы
    print(f"Ссылка на отзывы: {search_link}")

    uri = result['results'][0]['uri'] # URI Места в Яндекс Картах
    oid = uri.split('oid=')[1] # ID Места в Яндекс Картах
    print(f"OID: {oid}")

    print(f"Начинаем парсинг отзывов для {place_name}...")
    reviews = parse_yandex_reviews(search_link, reviews_number)
    
    if reviews:
        print(f"\nУспешно получено {len(reviews)} отзывов:\n")
        
        for i, review in enumerate(reviews, 1):
            print(f'Отзыв №{i}.\tДата: {review["date"]}')
            print(f'Автор: {review['author']}\tРейтинг: {review['rating']}/5.')
            print(f'Текст: {review["text"][:300]}...' if len(review['text']) > 300 else review["text"])
            print('-' * 80)
    else:
        print("Не удалось получить отзывы. Возможные причины.")
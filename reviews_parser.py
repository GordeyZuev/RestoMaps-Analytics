# Стандартная библиотека
import os
import time
import re

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
        
        # ID пользователя - извлекаем из различных источников
        user_id = None
        
        # Способ 1: Ищем в ссылках на профиль пользователя
        author_container = review_element.find('div', class_='business-review-view__author-container')
        if author_container:
            # Ищем ссылки на профиль пользователя
            user_links = author_container.find_all('a', href=True)
            for link in user_links:
                if '/maps/user/' in link['href']:
                    user_id = link['href'].split('/maps/user/')[-1].split('/')[0]
                    break
        
        # Способ 2: Ищем в URL аватара (если есть)
        if not user_id:
            avatar_div = review_element.find('div', class_='user-icon-view__icon')
            if avatar_div and 'style' in avatar_div.attrs:
                style = avatar_div['style']
                if 'background-image' in style:
                    # Извлекаем URL из background-image
                    import re
                    url_match = re.search(r'url\("([^"]+)"\)', style)
                    if url_match:
                        avatar_url = url_match.group(1)
                        # Пытаемся извлечь ID из URL аватара
                        if 'get-yapic' in avatar_url:
                            # Формат: https://avatars.mds.yandex.net/get-yapic/27274/BPqOCLuBQK5GpRrIDZudnicp1nQ-1/islands-68
                            parts = avatar_url.split('/')
                            if len(parts) >= 5:
                                user_id = parts[4]  # BPqOCLuBQK5GpRrIDZudnicp1nQ-1
        
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
        
        # Дата - извлекаем точную дату в ISO формате
        date_iso = None
        date_elem = review_element.find('span', class_='business-review-view__date')
        if date_elem:
            # Ищем meta тег с точной датой
            meta_date = date_elem.find('meta', itemprop='datePublished')
            if meta_date and 'content' in meta_date.attrs:
                date_iso = meta_date['content']
            else:
                # Если нет meta тега, используем текстовую дату
                date_iso = date_elem.get_text(strip=True)
        else:
            date_iso = "Дата не указана"
        
        return {
            'author': author,
            'user_id': user_id,
            'rating': rating,
            'text': text,
            'date_iso': date_iso
        }
    except Exception as e:
        print(f"Ошибка при извлечении данных отзыва: {e}")
        return None

def parse_yandex_reviews(url, max_reviews=-1, scroll_attempts=5):
    driver = setup_driver()
    try:
        driver.get(url)

        # --- Эмулируем нажатие на кнопку: Сортировка "По новизне" ---
        try:
            print("Пытаемся переключить сортировку на 'По новизне'...")
            
            # Ждём загрузки страницы
            time.sleep(3)
            
            # 1) Найти кнопку сортировки (пробуем разные селекторы)
            sort_selectors = [
                ".business-reviews-card-view__ranking .rating-ranking-view",
                ".rating-ranking-view",
                "[role='button'][aria-haspopup='true']",
                "div[class*='rating-ranking-view']"
            ]
            
            sort_btn = None
            for selector in sort_selectors:
                try:
                    sort_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    print(f"Найдена кнопка сортировки с селектором: {selector}")
                    break
                except:
                    continue
            
            if not sort_btn:
                print("Не удалось найти кнопку сортировки")
                return []
            
            # Прокручиваем к кнопке и кликаем
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_btn)
            time.sleep(1)
            
            # Пробуем разные способы клика
            try:
                sort_btn.click()
            except:
                try:
                    driver.execute_script("arguments[0].click();", sort_btn)
                except:
                    driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", sort_btn)
            
            print("Клик по кнопке сортировки выполнен")
            time.sleep(2)

            # 2) Дождаться выпадающего меню (пробуем разные селекторы)
            popup_selectors = [
                ".rating-ranking-view__popup",
                ".popup",
                "[class*='popup']",
                "[class*='dropdown']"
            ]
            
            popup = None
            for selector in popup_selectors:
                try:
                    popup = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"Найдено выпадающее меню с селектором: {selector}")
                    break
                except:
                    continue
            
            if not popup:
                print("Не удалось найти выпадающее меню")
                return []

            # 3) Кликнуть на пункт "По новизне" (пробуем разные способы поиска)
            newest_item = None
            search_methods = [
                (By.XPATH, ".//div[text()='По новизне']"),
                (By.XPATH, ".//span[text()='По новизне']"),
                (By.XPATH, ".//*[contains(text(), 'По новизне')]"),
                (By.CSS_SELECTOR, "[data-value='newest']"),
                (By.CSS_SELECTOR, "[class*='newest']")
            ]
            
            for method, selector in search_methods:
                try:
                    newest_item = popup.find_element(method, selector)
                    print(f"Найден пункт 'По новизне' с селектором: {method} - {selector}")
                    break
                except:
                    continue
            
            if not newest_item:
                print("Не удалось найти пункт 'По новизне' в меню")
                # Выводим все доступные пункты для отладки
                try:
                    all_items = popup.find_elements(By.XPATH, ".//div | .//span")
                    print("Доступные пункты в меню:")
                    for item in all_items:
                        text = item.text.strip()
                        if text:
                            print(f"  - {text}")
                except:
                    pass
                return []
            
            # Кликаем по пункту "По новизне"
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", newest_item)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", newest_item)
            
            print("Клик по пункту 'По новизне' выполнен")
            time.sleep(3)

            # 4) Подождать, пока меню исчезнет и сортировка применится
            try:
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element(popup)
                )
                print("Меню сортировки закрылось")
            except:
                print("Меню не закрылось автоматически, продолжаем...")
            
            # Дополнительное ожидание для применения сортировки
            time.sleep(3)
            print("Сортировка 'По новизне' применена успешно")
            
        except Exception as e:
            print(f"Не удалось переключиться на «По новизне»: {e}")
            print("Продолжаем без изменения сортировки...")
            
            # Альтернативный подход: попробуем найти и кликнуть по кнопке через JavaScript
            try:
                print("Пробуем альтернативный подход через JavaScript...")
                js_script = """
                // Ищем все элементы с текстом "По умолчанию" или похожие на кнопки сортировки
                const sortButtons = document.querySelectorAll('[role="button"], .rating-ranking-view, [class*="ranking"]');
                for (let btn of sortButtons) {
                    if (btn.textContent.includes('По умолчанию') || btn.textContent.includes('По рейтингу')) {
                        console.log('Найдена кнопка сортировки:', btn.textContent);
                        btn.click();
                        return true;
                    }
                }
                return false;
                """
                result = driver.execute_script(js_script)
                if result:
                    print("Альтернативный клик выполнен")
                    time.sleep(3)
                    
                    # Теперь ищем пункт "По новизне" в появившемся меню
                    js_script_newest = """
                    const menuItems = document.querySelectorAll('div, span');
                    for (let item of menuItems) {
                        if (item.textContent.trim() === 'По новизне') {
                            console.log('Найден пункт "По новизне"');
                            item.click();
                            return true;
                        }
                    }
                    return false;
                    """
                    newest_result = driver.execute_script(js_script_newest)
                    if newest_result:
                        print("Альтернативный клик по 'По новизне' выполнен")
                        time.sleep(3)
                    else:
                        print("Не удалось найти пункт 'По новизне' альтернативным способом")
                else:
                    print("Не удалось найти кнопку сортировки альтернативным способом")
            except Exception as alt_e:
                print(f"Альтернативный подход также не сработал: {alt_e}")

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

    reviews_number = 100
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
            print(f'Отзыв №{i}.')
            print(f'Автор: {review["author"]}')
            print(f'ID пользователя: {review["user_id"] or "Не найден"}')
            print(f'Дата (ISO): {review["date_iso"]}')
            print(f'Рейтинг: {review["rating"]}/5')
            print(f'Текст: {review["text"][:300]}...' if len(review['text']) > 300 else review["text"])
            print('-' * 80)
    else:
        print("Не удалось получить отзывы. Возможные причины.")
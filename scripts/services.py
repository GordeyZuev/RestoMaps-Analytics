import asyncio
from typing import Any

import httpx

from config.settings import settings
from logger import logger


async def get_coord_by_address(address: str) -> dict[str, Any] | None:
    """Получение координат по адресу через Яндекс.Геокодер API."""
    if not settings.YA_GEO_CODER_API_KEY:
        logger.warning("YA_GEO_CODER_API_KEY не установлен — геокодирование недоступно")
        return None

    url = "https://geocode-maps.yandex.ru/v1/?"
    params = {
        "geocode": address,
        "apikey": settings.YA_GEO_CODER_API_KEY,
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Геокодирование адреса инициировано: '{address}'")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            feature_member = data["response"]["GeoObjectCollection"]["featureMember"]
            if feature_member:
                geo_object = feature_member[0]["GeoObject"]
                point = geo_object["Point"]
                coords = point["pos"].split()
                longitude, latitude = float(coords[0]), float(coords[1])

                result = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "full_address": geo_object["metaDataProperty"]["GeocoderMetaData"][
                        "text"
                    ],
                }
                logger.info(
                    f"Геокодирование успешно: '{address}' -> "
                    f"({result['latitude']}, {result['longitude']})"
                )
                return result
            return None

        except Exception:
            logger.exception(f"Ошибка при геокодировании адреса: '{address}'")
            return None


if __name__ == "__main__":
    test_address = "Страстной бул., 12, стр. 5, Москва"
    logger.info(f"Тест геокодирования — адрес: {test_address}")

    coord = asyncio.run(get_coord_by_address(test_address))

    if coord:
        logger.info(f"Широта: {coord['latitude']}")
        logger.info(f"Долгота: {coord['longitude']}")
        logger.info(f"Полный адрес: {coord['full_address']}")
    else:
        logger.warning("Координаты не найдены")

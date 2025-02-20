import asyncio
import os

from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import country_converter as coco
import deepl
import logging
load_dotenv(dotenv_path=r"C:\Users\Данил\PycharmProjects\Test_keymakr\Test_Keymakr\local_data.env")
logger = logging.getLogger('Test_Keymakr')

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
def get_country(city):
    geolocator = Nominatim(user_agent="test_work")
    location = geolocator.geocode(city, exactly_one=True)

    if not location:
        logger.warning(f"Не вдалося знайти місцезнаходження для {city}")
        return None

    address_parts = location.raw.get("display_name", "").split(", ")
    country_name = address_parts[-1] if address_parts else None

    if not country_name:
        logger.warning(f"Країну для {city} не знайдено")
        return None

    return country_name


def get_continent_by_country(country_name):
    return coco.convert(names=country_name, to='continent') or "Unknown"


def main(cities:list):
    region_country_dict = {}
    translator = deepl.Translator(DEEPL_API_KEY)
    for city in cities:
        country = get_country(city)
        if not country:
            continue

        try:
            # Перевод с украинского на английский

            translated_country = translator.translate_text(city, source_lang="UK", target_lang="EN-US")
            logger.info(f"Translated {country} to {translated_country}")
        except Exception as e:
            logger.error(f"Translation failed for {country}: {e}")
            # Fallback: Use the original country name if translation fails
            translated_country = country

        continent = get_continent_by_country(translated_country)

        if continent not in region_country_dict:
            region_country_dict[continent] = []
        region_country_dict[continent].append(translated_country)

    return region_country_dict

main(["Kyiv","Lviv","London"])
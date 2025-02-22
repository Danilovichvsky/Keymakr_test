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
    """
    Function to get country by city.
    """
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
    """
    Function to get continent (region) by country.
    """
    return coco.convert(names=country_name, to='continent') or "Unknown"


def main_convert(city):
    """
    Main function to convert city to continent.
    """
    region_country_dict = {}
    translator = deepl.Translator(DEEPL_API_KEY)


    # Переводим название города на английский (если есть в словаре)
    translated_city = translator.translate_text(city, source_lang="UK", target_lang="EN-US")

    # Получаем страну для города
    country = get_country(translated_city)
    if not country:
        logger.error(f"Не вдалося знайти країну для міста {city}")
        return region_country_dict  # Возвращаем пустой словарь, если страна не найдена

    try:
        translated_country = translator.translate_text(country, source_lang="UK", target_lang="EN-US")
        translated_country_name = translated_country.text  # Извлекаем текст перевода
        logger.info(f"Translated {country} to {translated_country_name}")
    except Exception as e:
        logger.error(f"Translation failed for {country}: {e}")
        translated_country_name = country

    # Получаем континент для переведенной страны
    continent = get_continent_by_country(translated_country_name)

    # Добавляем данные в словарь
    if continent not in region_country_dict:
        region_country_dict[continent] = []
    region_country_dict[continent].append({
        "city": translated_city,  # Используем переведенное название города
    })

    return region_country_dict



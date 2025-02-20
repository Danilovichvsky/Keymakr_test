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


def main_convert(city):
    region_country_dict = {}
    translator = deepl.Translator(DEEPL_API_KEY)

    # Словарь для перевода городов на английский
    city_translation_dict = {
        "Киев": "Kyiv",
        "Токио": "Tokyo",
        # Добавьте другие города по необходимости
    }

    # Переводим название города на английский (если есть в словаре)
    translated_city = city_translation_dict.get(city, city)

    # Получаем страну для города
    country = get_country(translated_city)
    if not country:
        logger.error(f"Не вдалося знайти країну для міста {city}")
        return region_country_dict  # Возвращаем пустой словарь, если страна не найдена

    try:
        # Переводим название страны на английский
        translated_country = translator.translate_text(country, source_lang="UK", target_lang="EN-US")
        translated_country_name = translated_country.text  # Извлекаем текст перевода
        logger.info(f"Translated {country} to {translated_country_name}")
    except Exception as e:
        logger.error(f"Translation failed for {country}: {e}")
        # Используем оригинальное название страны, если перевод не удался
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

if __name__=='__main__':
    """
    Test 
    """
    try:
        tokyo_country = get_country("Київ")
        tokyo_cont = get_continent_by_country(tokyo_country)
        print(tokyo_cont)
    except Exception as e:
        print(e)
    DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
    print(os.getenv("DEEPL_API_KEY"))
    if not DEEPL_API_KEY:
        raise ValueError("API-ключ DeepL не найден в переменных окружения")

    translator = deepl.Translator(DEEPL_API_KEY)

    translated_country = translator.translate_text("Україна", source_lang="UK", target_lang="EN-US")
    print(translated_country)




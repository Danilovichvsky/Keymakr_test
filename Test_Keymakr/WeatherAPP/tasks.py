import json
import os
import time
import deepl
import geonamescache
import requests
from celery import shared_task
from dotenv import load_dotenv
from fuzzywuzzy import process
from django.conf import settings
import logging
from .convert_cont import main_convert
from .models import WeatherTask

logger = logging.getLogger('Test_Keymakr')
load_dotenv(dotenv_path=r"C:\Users\Данил\PycharmProjects\Test_keymakr\Test_Keymakr\local_data.env")

WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")


@shared_task(bind=True)
def process_weather_data(self, cities, task_id):
    logger.info("Cities to process: %s", cities)
    results = {}
    error_info = None

    try:
        task = WeatherTask.objects.get(task_id=task_id)
        for city in cities:
            normalized_city = normalize_city_name(city, task_id)
            if not normalized_city:
                error_info = f"Error with normalization for {city}"
                logger.error(error_info)
                continue

            weather_data = fetch_weather_data(normalized_city)
            if not weather_data or not validate_weather_data(weather_data):
                error_info = f"Error with validation or fetching weather data for {city}"
                logger.error(error_info)
                continue

            region = classify_region(normalized_city, task_id)
            if not region:
                task.status = "failed"
                error_info = f"Error classifying region for {city}"
                logger.error(error_info)
                continue

            if region not in results:
                results[region] = []
            translator = deepl.Translator(DEEPL_API_KEY)

            # Переводим название города на английский (если есть в словаре)
            translated_description = translator.translate_text(str(weather_data["condition"].get("description", "N/A")),
                                                               source_lang="UK", target_lang="EN-US").text
            results[region].append({
                "city": normalized_city,
                "temperature": weather_data["temp_c"],
                "description": translated_description
            })

        if error_info:
            task.status = "failed"
            task.result = {
                "results": results,
                "error": error_info,
                "failed_task_id": task_id
            }
            task.save()
            logger.info(f"Task {task_id} marked as failed with error: {error_info}")
            return {"status": "failed", "results": results, "error": error_info, "failed_task_id": task_id}

        if not results:
            task.status = "failed"
            task.result = {
                "results": {},
                "error": "No data processed",
                "failed_task_id": task_id
            }
            task.save()
            logger.info(f"Task {task_id} marked as failed due to empty results")
            return {"status": "failed", "results": {}, "error": "No data processed", "failed_task_id": task_id}

        save_results(task_id, results)
        return {"status": "completed", "results": results}

    except Exception as e:
        task = WeatherTask.objects.get(task_id=task_id)
        logger.error(f"Error processing task {task_id}: {e}")
        task.status = "failed"
        task.result = {
            "results": results,
            "error": str(e),
            "failed_task_id": task_id
        }
        task.save()
        return {"status": "failed", "results": results, "error": str(e), "failed_task_id": task_id}


def get_all_cities():
    """Getting all cities with added PRIORITY_CITIES for improving for finding """

    PRIORITY_CITIES = {"New York", "Los Angeles", "San Francisco", "London"}
    gc = geonamescache.GeonamesCache()
    cities = [city_data["name"] for city_data in gc.get_cities().values()]
    return list(set(cities) | PRIORITY_CITIES)  # Добавляем приоритетные города


def normalize_city_name(city,task_id):
    """ Normalization for city. Corrects correct words of cities """
    known_cities = get_all_cities()

    # Пробуем сначала найти прямое совпадение
    matched = process.extractOne(city, known_cities)
    matched_city, score = matched
    if score < 50:
        translator = deepl.Translator(DEEPL_API_KEY)
        translated_city = translator.translate_text(city, source_lang="UK", target_lang="EN-US").text
        matched = process.extractOne(translated_city, known_cities)

    matched_city, score = matched
    if score > 80:
        logger.info(f"Normalized {city} to {matched_city}")
        return matched_city
    else:
        task = WeatherTask.objects.get(task_id=task_id)
        task.status = "completed"
        task.save()  # Сохраняем задачу в базе данных
        logger.warning(f"Problem with getting city {city}")


def fetch_weather_data(city):
    """ Collects weather data in the city """
    try:
        response = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": WEATHER_API_KEY, "units": "metric", "lang": "ru"},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return {
            "temp_c": data.get("main", {}).get("temp"),
            "condition": data.get("weather", [{}])[0]
        }
    except requests.RequestException as e:
        logger.error(f"Error fetching weather data for {city}: {e}")
        return None


def validate_weather_data(data):
    """ Validates city weather data """
    temp = data.get("temp_c")
    if temp is None:
        logger.warning(f"Temperature is missing for data: {data}")
        return False
    if not (-50 <= temp <= 50):
        logger.warning(f"Temperature {temp} is out of range for data: {data}")
        return False
    return True


def classify_region(city, task_id):
    """ Receives the city region """
    region_data = main_convert(city)  # Pass a list with one city
    if not region_data or "not found" in region_data.keys():
        task = WeatherTask.objects.get(task_id=task_id)
        task.status = "failed"
        task.save()  # Сохраняем задачу в базе данных
        logger.warning(f"Task {task_id} marked as failed")
        return None
    return list(region_data.keys())[0] if region_data else "Unknown"


def save_results(task_id, results):
    """ Saves results to file """
    base_dir = os.path.join(settings.BASE_DIR, "weather_data")
    os.makedirs(base_dir, exist_ok=True)
    file_paths = []

    for region, data in results.items():
        if data:
            region_dir = os.path.join(base_dir, region)
            os.makedirs(region_dir, exist_ok=True)
            filename = os.path.join(region_dir, f"task_{task_id}.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved results for {region} in {filename}")
            file_paths.append(filename)


    if file_paths:
        try:
            task = WeatherTask.objects.get(task_id=task_id)
            if not task.status == "failed":
                task.result = {
                    "results": results,  # Все успешно обработанные данные
                }
                task.status = "completed"
                task.result["file_path"] = file_paths  # Устанавливаем пути в поле result
                task.save()  # Сохраняем задачу в базе данных
                logger.info(f"Task {task_id} marked as completed with results saved at: {file_paths}")
        except WeatherTask.DoesNotExist:
            logger.error(f"Task {task_id} not found in the database")
        except Exception as e:
            logger.error(f"Error updating task {task_id} status: {e}")
    else:
        logger.error(f"No valid file paths found for task {task_id}")

    return file_paths

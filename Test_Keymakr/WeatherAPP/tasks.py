import asyncio
import json
import os
import time

import requests
from celery import shared_task
from dotenv import load_dotenv
from fuzzywuzzy import process
from django.conf import settings
import logging
import country_converter as coco
from .convert_cont import main_convert
from .models import WeatherTask

logger = logging.getLogger('Test_Keymakr')
load_dotenv(dotenv_path=r"C:\Users\Данил\PycharmProjects\Test_keymakr\Test_Keymakr\local_data.env")

WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')


@shared_task(bind=True)
def process_weather_data(self, cities, task_id):
    logger.info("Cities to process: %s", cities)

    try:
        results = {}

        for city in cities:
            normalized_city = normalize_city_name(city)
            if not normalized_city:
                logger.info(f"Помилка при нормалізації міста {city}")
                continue

            weather_data = fetch_weather_data(normalized_city)
            if not weather_data or not validate_weather_data(weather_data):
                logger.info(f"Помилка виникла при діставання даних про погоду для міста {city}")
                continue

            # Get the region for the city
            region = classify_region(normalized_city)
            if region not in results:
                results[region] = []
            results[region].append({
                "city": normalized_city,
                "temperature": weather_data["temp_c"],
                "description": weather_data["condition"].get("description", "N/A")
            })

        if results == {}:
            try:
                task = WeatherTask.objects.get(task_id=task_id)
                task.status = "failed"
                task.save()
                logger.info(f"Task {task_id} marked as completed")
            except WeatherTask.DoesNotExist:
                logger.error(f"Task {task_id} not found in the database")
            except Exception as e:
                logger.error(f"Error updating task {task_id} status: {e}")
        save_results(task_id, results)
        return results
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}")
        self.update_state(state="FAILED", meta={"exc": str(e)})
        raise


def normalize_city_name(city):
    known_cities = ["Kyiv", "London", "New York", "Tokyo", "Lviv"]
    matched_city, score = process.extractOne(city, known_cities)
    if score > 80:
        logger.info(f"Normalized {city} to {matched_city}")
        return matched_city
    else:
        logger.warning(f"Could not normalize {city}")
        return None


def fetch_weather_data(city):
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
    temp = data.get("temp_c")
    if temp is None:
        logger.warning(f"Temperature is missing for data: {data}")
        return False
    if not (-50 <= temp <= 50):
        logger.warning(f"Temperature {temp} is out of range for data: {data}")
        return False
    return True


def classify_region(city):
    region_data = main_convert(city)  # Pass a list with one city
    return list(region_data.keys())[0] if region_data else "Unknown"


def save_results(task_id, results):
    base_dir = os.path.join(settings.BASE_DIR, "weather_data")
    os.makedirs(base_dir, exist_ok=True)
    for region, data in results.items():
        if data:
            region_dir = os.path.join(base_dir, region)
            os.makedirs(region_dir, exist_ok=True)
            filename = os.path.join(region_dir, f"task_{task_id}.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)  # Ensure proper UTF-8 encoding
            logger.info(f"Saved results for {region} in {filename}")
    #time.sleep(20)
    try:
        task = WeatherTask.objects.get(task_id=task_id)
        task.status = "completed"
        task.save()
        logger.info(f"Task {task_id} marked as completed")
    except WeatherTask.DoesNotExist:
        logger.error(f"Task {task_id} not found in the database")
    except Exception as e:
        logger.error(f"Error updating task {task_id} status: {e}")

import os
import sys
import deepl
import django
from dotenv import load_dotenv
from WeatherAPP.convert_cont import main_convert

# Добавляем путь к проекту
sys.path.append("C:/Users/Данил/PycharmProjects/Test_keymakr")

# Указываем Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Test_Keymakr.settings")

# Инициализация Django (до импорта моделей!)
django.setup()

# Теперь можно импортировать модели
from WeatherAPP.models import WeatherTask

# Настройка логгера для поддержки Unicode
import logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
    encoding='utf-8'  # Указываем кодировку для логов
)

# Запрос к БД
ctasks = WeatherTask.objects.filter(status="completed")
all_path = []
for t in ctasks:
    completed_results = t.result.get("results", {}).get("Europe", [])
    file_paths = t.result.get("file_path", [])
    for path in file_paths:
        if "Europe" in path:
            all_path.append(path)

# Вывод результатов
print({"region": "Europe", "cities": completed_results, "paths": all_path})

# Пример перевода
load_dotenv(dotenv_path=r"C:\Users\Данил\PycharmProjects\Test_keymakr\Test_Keymakr\local_data.env")
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
translator = deepl.Translator(DEEPL_API_KEY)

try:
    translated_description = translator.translate_text("Бангкок", source_lang="UK", target_lang="EN-US")
    print(f"Перекладено опис: {translated_description.text}")
except Exception as e:
    print(f"Помилка перекладу: {e}")

# Пример использования main_convert
region_data = main_convert("Bangkok")
print(f"Дані для міста Bangkok: {region_data}")
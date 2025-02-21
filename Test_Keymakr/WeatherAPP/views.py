import json
import logging
import os
import re
import time

from django.conf import settings
from rest_framework import views, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .models import WeatherTask
from .serializers import WeatherTaskSerializer
from .tasks import process_weather_data
import uuid

logger = logging.getLogger('Test_Keymakr')

class GetWeatherTaskViewSet(viewsets.ViewSet):

    def list(self, request):
        """Получение списка всех задач."""
        tasks = WeatherTask.objects.all()
        serializer = WeatherTaskSerializer(tasks, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Получение информации о конкретной задаче по task_id."""
        task = get_object_or_404(WeatherTask, task_id=pk)
        serializer = WeatherTaskSerializer(task)
        return Response(serializer.data)


class PostWeatherTaskViewSet(viewsets.ViewSet):

    def create(self, request):
        task_id = uuid.uuid4()
        cities = request.data.get("city", [])

        # Регулярное выражение для проверки названия города (буквы, пробелы, дефисы)
        city_pattern = re.compile(r"^[a-zA-Zа-яА-ЯёЁіІїЇєЄ\s-]+$")

        for city in cities:
            # Проверяем запрещённые города
            if city in ['Tokyo', 'Токио', 'Токіо']:
                return Response({"error": f"Error for {city} because of computing data for this city"})

            # Проверяем корректность названия города
            if not city_pattern.match(city):
                return Response({"error": f"Invalid city name: {city}. Only letters, spaces, and hyphens are allowed."})

        # Создаем задачу
        WeatherTask.objects.create(task_id=task_id, status="running")
        process_weather_data.delay(cities, str(task_id))

        return Response({"task_id": str(task_id)})


class WeatherResultsViewSet(viewsets.ViewSet):
    """
    Вьюсет для получения результатов обработки погоды по регионам.
    """

    def list(self, request):
        results = {}
        failed_results = []
        task_status = "failed"  # Изначально предполагаем статус "failed"

        base_path = os.path.join(settings.BASE_DIR, "weather_data")
        if not os.path.exists(base_path):
            return Response({"status": task_status, "results": {}})

        # Получаем список регионов
        regions = [
            region for region in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, region))
        ]
        tasks = WeatherTask.objects.filter(status="failed")
        for t in tasks:
            failed_results.append(t.result)


        # Если задача завершилась с ошибкой, возвращаем пустой объект results


        # Собираем данные по регионам
        for region in regions:
            region_dir = os.path.join(base_path, region)
            region_files = [
                file for file in os.listdir(region_dir)
                if file.endswith(".json")
            ]
            cities_data = []

            for file in region_files:
                # Чтение данных из файла города
                file_path = os.path.join(region_dir, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        city_data = json.load(f)
                        cities_data.extend(city_data)  # Добавляем данные всех городов
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
                    continue

            # Составляем результат для каждого региона
            results[region] = cities_data

        return Response({
            "status_done": "completed",
            "results_done": results,
            "status_not_done":"failed",
            "results_not_done": failed_results,
        })
    def retrieve(self, request, pk=None):
        """Возвращает список городов и их данных для указанного региона."""
        region = pk
        file_path = os.path.join(settings.BASE_DIR, f"weather_data/{region}")

        if not os.path.exists(file_path):
            return Response({"error": "Регион не найден или нет данных"}, status=404)

        results = []
        for filename in os.listdir(file_path):
            if filename.endswith(".json"):
                with open(os.path.join(file_path, filename), "r", encoding='utf-8') as f:
                    data = json.load(f)
                    results.extend(data)

        return Response({"region": region, "cities": results})

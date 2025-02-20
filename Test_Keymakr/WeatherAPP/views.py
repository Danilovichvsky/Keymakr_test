import json
import os
import time

from django.conf import settings
from rest_framework import views, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .models import WeatherTask
from .serializers import WeatherTaskSerializer
from .tasks import process_weather_data
import uuid


class GetWeatherTaskViewSet(viewsets.ViewSet):
    """
        В'юсет для отримання даних про таски
    """

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
    """
        В'юсет для додавання таски
    """

    def create(self, request):
        task_id = uuid.uuid4()
        cities = request.data.get("city", [])
        print(cities)
        WeatherTask.objects.create(task_id=task_id)
        created_task = WeatherTask.objects.get(task_id=task_id)
        created_task.status = "running"
        created_task.save()
        process_weather_data.delay(cities, task_id)
        return Response({"task_id": task_id})


class WeatherResultsViewSet(viewsets.ViewSet):
    """
    Вьюсет для получения результатов обработки погоды по регионам.
    """

    def list(self, request):
        """Возвращает список доступных регионов с данными."""
        base_path = os.path.join(settings.BASE_DIR, "weather_data")
        if not os.path.exists(base_path):
            return Response({"regions": []})

        regions = [
            region for region in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, region))
        ]
        return Response({"regions": regions})

    def retrieve(self, request, pk=None):
        """Возвращает список городов и их данных для указанного региона."""
        region = pk
        file_path = os.path.join(settings.BASE_DIR, f"weather_data/{region}")

        if not os.path.exists(file_path):
            return Response({"error": "Регион не найден или нет данных"}, status=404)

        results = []
        for filename in os.listdir(file_path):
            if filename.endswith(".json"):
                with open(os.path.join(file_path, filename), "r") as f:
                    data = json.load(f)
                    results.extend(data)

        return Response({"region": region, "cities": results})

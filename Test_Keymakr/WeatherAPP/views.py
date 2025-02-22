import logging
import re
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
    """
    Viewset to get all or a specific task.
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
    Viewset for sending cities to get data about the region and weather.
    """

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
    Viewset for obtaining weather processing results by region and for getting all data with all regions.
    """

    def list(self, request):
        completed_results = []
        failed_results = []

        ftasks = WeatherTask.objects.filter(status="failed")
        for t in ftasks:
            failed_results.append(t.result)

        ctasks = WeatherTask.objects.filter(status="completed")
        for t in ctasks:
            completed_results.append(t.result)

        return Response({
            "status_done": "completed",
            "results_done": completed_results,
            "status_not_done": "failed",
            "results_not_done": failed_results,
        })

    def retrieve(self, request, pk=None):
        completed_results = []
        path_with_regions = []
        """Возвращает список городов и их данных для указанного региона."""
        region = pk
        ctasks = WeatherTask.objects.filter(status="completed")

        for t in ctasks:
            if t.result and "results" in t.result:
                if region in t.result["results"]:  #
                    completed_results.extend(t.result["results"][region])
                else:
                    logger.error(f"The region '{region}' not found in task {t.task_id}")

            if t.result and "file_path" in t.result:
                file_path = t.result["file_path"]
                if isinstance(file_path, list):
                    for path in file_path:
                        if region in path:
                            path_with_regions.append(path)
                elif isinstance(file_path, str):
                    if region in file_path:
                        path_with_regions.append(file_path)

        if not completed_results:
            logger.error(f"No data found for region '{region}'")

        return Response({
            "region": region,
            "cities": completed_results,
            "path": path_with_regions
        })

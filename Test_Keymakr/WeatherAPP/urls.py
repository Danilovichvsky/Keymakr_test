from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import GetWeatherTaskViewSet, PostWeatherTaskViewSet, WeatherResultsViewSet

router = DefaultRouter()
router.register(r'tasks', GetWeatherTaskViewSet,basename="get-task")
router.register(r'weather', PostWeatherTaskViewSet,basename="create-task")
router.register(r'results',WeatherResultsViewSet,basename="get-task-result")

# Подключаем маршруты
urlpatterns = [
    path('', include(router.urls)),
]

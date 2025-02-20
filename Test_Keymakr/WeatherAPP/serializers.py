from rest_framework import serializers
from .models import WeatherTask

class WeatherTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherTask
        fields = '__all__'

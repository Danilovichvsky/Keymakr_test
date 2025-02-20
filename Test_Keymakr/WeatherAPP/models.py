from django.db import models


class WeatherTask(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50, default='running')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    result = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Task {self.task_id} - {self.status}"

    class Meta:
        db_table = "WeatherTask"
from django.db import models
from django.contrib.auth.models import User
import json

class AnalysisResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    input_text = models.TextField()
    entities = models.JSONField(default=list)
    visualization_html = models.TextField()
    morph_analysis = models.JSONField(default=list)  # Добавьте это поле
    analysis_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Анализ от {self.analysis_date}"

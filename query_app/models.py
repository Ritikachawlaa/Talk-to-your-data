from django.db import models
from django.utils import timezone

class DatasetUpload(models.Model):
    """Store information about uploaded datasets"""
    file_name = models.CharField(max_length=255)
    upload_date = models.DateTimeField(default=timezone.now)
    row_count = models.IntegerField(null=True, blank=True)
    column_count = models.IntegerField(null=True, blank=True)
    columns = models.TextField(help_text="Comma-separated list of column names")
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.file_name} ({self.upload_date.strftime('%Y-%m-%d %H:%M')})"


class QueryHistory(models.Model):
    """Store query history with results"""
    dataset = models.ForeignKey(DatasetUpload, on_delete=models.CASCADE, null=True, blank=True)
    query_text = models.TextField()
    query_date = models.DateTimeField(default=timezone.now)
    
    # Generated code
    python_code = models.TextField(blank=True)
    sql_command = models.TextField(blank=True)
    
    # Results
    result_data = models.TextField(blank=True, help_text="Query result as string")
    has_chart = models.BooleanField(default=False)
    chart_image = models.TextField(blank=True, help_text="Base64 encoded chart image")
    
    # Execution info
    execution_success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    execution_time_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-query_date']
        verbose_name_plural = "Query histories"
    
    def __str__(self):
        return f"{self.query_text[:50]}... ({self.query_date.strftime('%Y-%m-%d %H:%M')})"

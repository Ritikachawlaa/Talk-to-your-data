from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('download-csv/', views.download_csv, name='download_csv'),
    
    # Evaluation endpoints (Research Objectives 2 & 3)
    path('evaluation/', views.evaluation_dashboard, name='evaluation_dashboard'),
    path('evaluation/run/', views.run_evaluation, name='run_evaluation'),
    path('evaluation/download-results/', views.download_evaluation_results, name='download_evaluation_results'),
    path('evaluation/download-comparison/', views.download_comparison_csv, name='download_comparison_csv'),
]

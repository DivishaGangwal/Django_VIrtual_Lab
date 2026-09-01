"""
URL routing for Virtual Lab application.
"""

from django.urls import path
from . import views

app_name = 'virtual_lab'

urlpatterns = [
    # Laboratory Pages
    path('', views.aim_view, name='aim'),
    path('theory/', views.theory_view, name='theory'),
    path('procedure/', views.procedure_view, name='procedure'),
    path('simulation/', views.simulation_view, name='simulation'),
    path('observations/', views.observations_view, name='observations'),
    path('quiz/', views.quiz_view, name='quiz'),

    # Developer 1 Ingestion APIs
    path('api/upload-csv/', views.upload_csv_api, name='api_upload_csv'),
    path('api/load-sample/', views.load_sample_api, name='api_load_sample'),
]

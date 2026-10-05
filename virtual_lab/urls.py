"""
URL routing for Virtual Lab application.
"""

from django.urls import path

from . import views

app_name = 'virtual_lab'

urlpatterns = [
    # Laboratory pages
    path('', views.aim_view, name='aim'),
    path('theory/', views.theory_view, name='theory'),
    path('procedure/', views.procedure_view, name='procedure'),
    path('simulation/', views.simulation_view, name='simulation'),
    path('observations/', views.observations_view, name='observations'),
    path('observations/export.csv', views.export_observations_csv, name='export_observations'),
    path('quiz/', views.quiz_view, name='quiz'),

    # JSON APIs
    path('api/upload-csv/', views.upload_csv_api, name='api_upload_csv'),
    path('api/load-sample/', views.load_sample_api, name='api_load_sample'),
    path('api/dataset/', views.dataset_api, name='api_dataset'),
    path('api/dataset/reset/', views.reset_dataset_api, name='api_reset_dataset'),
    path('api/chart-data/', views.chart_data_api, name='api_chart_data'),
    path('api/quiz/submit/', views.submit_quiz_api, name='api_submit_quiz'),
]

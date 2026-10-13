"""
URL routing for Virtual Lab application.
"""

from django.urls import path

from . import views

app_name = 'virtual_lab'

urlpatterns = [
    # Laboratory pages (in step order)
    path('', views.aim_view, name='aim'),
    path('theory/', views.theory_view, name='theory'),
    path('pretest/', views.pretest_view, name='pretest'),
    path('procedure/', views.procedure_view, name='procedure'),
    path('simulation/', views.simulation_view, name='simulation'),
    path('observations/', views.observations_view, name='observations'),
    path('observations/export.csv', views.export_observations_csv, name='export_observations'),
    path('posttest/', views.posttest_view, name='posttest'),
    path('references/', views.references_view, name='references'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('quiz/', views.quiz_redirect_view, name='quiz'),  # old URL → Posttest

    # JSON APIs
    path('api/upload-csv/', views.upload_csv_api, name='api_upload_csv'),
    path('api/load-sample/', views.load_sample_api, name='api_load_sample'),
    path('api/dataset/', views.dataset_api, name='api_dataset'),
    path('api/dataset/reset/', views.reset_dataset_api, name='api_reset_dataset'),
    path('api/chart-data/', views.chart_data_api, name='api_chart_data'),
    path('api/assessment/submit/', views.submit_assessment_api, name='api_submit_assessment'),
    path('api/rating/', views.submit_rating_api, name='api_submit_rating'),
    path('api/bug-report/', views.submit_bug_report_api, name='api_submit_bug_report'),
    path('api/feedback/', views.submit_feedback_api, name='api_submit_feedback'),
]

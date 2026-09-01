"""
URL configuration for lab_csv_visualizer project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('virtual_lab.urls')),
]

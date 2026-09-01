"""
ASGI config for lab_csv_visualizer project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lab_csv_visualizer.settings')
application = get_asgi_application()

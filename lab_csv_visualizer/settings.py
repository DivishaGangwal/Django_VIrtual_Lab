"""
Django settings for lab_csv_visualizer project.
Computer Engineering Virtual Lab: Reading and Visualizing CSV Data in Django.

Development defaults work out of the box. For anything beyond a local machine,
set these environment variables instead of editing this file:
    DJANGO_SECRET_KEY, DJANGO_DEBUG (0/1), DJANGO_ALLOWED_HOSTS (comma-separated)
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-only-virtual-lab-csv-visualizer-change-me',
)

DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
    if h.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'virtual_lab',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lab_csv_visualizer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # App templates live in virtual_lab/templates/ and are found via APP_DIRS.
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'virtual_lab.context_processors.lab_navigation',
            ],
        },
    },
]

WSGI_APPLICATION = 'lab_csv_visualizer.wsgi.application'

# SQLite stores sessions (the active dataset) and quiz attempts.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files. App static files (virtual_lab/static/) are found automatically
# by AppDirectoriesFinder, so STATICFILES_DIRS is intentionally not set
# (listing the same folder twice causes duplicate-file warnings in collectstatic).
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Uploads: 5 MB limit (also enforced in forms.py and in the browser).
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Sessions hold the active dataset between pages.
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 1 day

# Safety cap on rows kept in the session (keeps the session table small).
LAB_MAX_ROWS = 20000

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

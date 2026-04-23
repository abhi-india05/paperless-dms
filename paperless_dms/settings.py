import os
import re
from pathlib import Path

import pymysql
pymysql.install_as_MySQLdb()
# ──────────────────────────────────────────────────────────────────────────────
# Base Paths
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(env_path):
    """Load simple KEY=VALUE lines from an .env file into process env."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            os.environ[key] = value


_load_env_file(BASE_DIR / '.env')


def _dedupe_preserve_order(values):
    seen = set()
    deduped = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _split_api_keys(raw_value):
    if not raw_value:
        return []
    return _dedupe_preserve_order(
        chunk.strip()
        for chunk in re.split(r'[\n,;]+', raw_value)
        if chunk.strip()
    )


def _load_gemini_api_keys():
    numbered_keys = []
    for env_name, env_value in os.environ.items():
        if not env_name.startswith('GEMINI_API_KEY_'):
            continue

        suffix = env_name.removeprefix('GEMINI_API_KEY_')
        if suffix.isdigit():
            numbered_keys.append((int(suffix), env_value.strip()))

    if numbered_keys:
        numbered_keys.sort(key=lambda item: item[0])
        return _dedupe_preserve_order(value for _, value in numbered_keys)

    list_value = os.environ.get('GEMINI_API_KEYS', '').strip()
    if list_value:
        return _split_api_keys(list_value)

    single_value = os.environ.get('GEMINI_API_KEY', '').strip()
    return _split_api_keys(single_value)

# SECURITY WARNING: Change this in production!
SECRET_KEY = 'django-insecure-paperless-dms-college-project-secret-key-2024'

# ──────────────────────────────────────────────────────────────────────────────
# Gemini / Chatbot
# ──────────────────────────────────────────────────────────────────────────────
GEMINI_API_KEYS = _load_gemini_api_keys()
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ''
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash').strip() or 'gemini-1.5-flash'

# SECURITY WARNING: Don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# ──────────────────────────────────────────────────────────────────────────────
# Application Definition
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'documents',   # Our single app
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

ROOT_URLCONF = 'paperless_dms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],          # App templates are found via APP_DIRS=True
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'paperless_dms.wsgi.application'

# ──────────────────────────────────────────────────────────────────────────────
# Database — MySQL / Aiven
# ──────────────────────────────────────────────────────────────────────────────
MYSQL_SSL_CA = os.environ.get('MYSQL_SSL_CA', '').strip()
MYSQL_SSL_MODE = os.environ.get('MYSQL_SSL_MODE', 'REQUIRED').strip().upper()

mysql_options = {
    'charset': 'utf8mb4',
}

mysql_options = {
    'charset': 'utf8mb4',
}

if MYSQL_SSL_CA and Path(MYSQL_SSL_CA).exists():
    mysql_options['ssl'] = {'ca': MYSQL_SSL_CA}
else:
    mysql_options['ssl'] = {}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MYSQL_DATABASE', 'paperless_dms'),
        'USER': os.environ.get('MYSQL_USER', 'root'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD', 'your_password'),
        'HOST': os.environ.get('MYSQL_HOST', 'localhost'),
        'PORT': os.environ.get('MYSQL_PORT', '3306'),
        'OPTIONS': mysql_options,
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# Password Validation
# ──────────────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ──────────────────────────────────────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────────────────────
# Static & Media Files
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ──────────────────────────────────────────────────────────────────────────────
# Authentication Redirects
# ──────────────────────────────────────────────────────────────────────────────
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ──────────────────────────────────────────────────────────────────────────────
# Default Primary Key
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ──────────────────────────────────────────────────────────────────────────────
# File Upload Limits
# ──────────────────────────────────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'documents': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

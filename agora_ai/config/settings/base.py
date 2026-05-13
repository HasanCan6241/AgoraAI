# PATH: config/settings/base.py
"""
Agora AI — Temel (Ortak) Django Ayarları
Doküman Bölüm 2 (Tech Stack) ve Bölüm 3 (Mimari) referans alınmıştır.
Bu dosya tüm ortamlar (dev, prod) tarafından import edilir.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# ── Temel Yollar ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# ── Güvenlik ─────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY")

# ── Uygulama Tanımları ────────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_ratelimit",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.philosophers",
    "apps.conversations",
    "apps.rag",
    "apps.symposium",
    "apps.glossary",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ── URL Yönlendirme ───────────────────────────────────────────────────────────
ROOT_URLCONF = "config.urls"

# ── Şablonlar ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ── WSGI / ASGI ───────────────────────────────────────────────────────────────
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Veritabanı (Doküman Bölüm 4.1) ──────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "agora_ai"),
        "USER": os.environ.get("DB_USER", "agora_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "agora_password"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# ── Özel Kullanıcı Modeli (Doküman Bölüm 4.1.1) ─────────────────────────────
AUTH_USER_MODEL = "accounts.CustomUser"

# ── Şifre Doğrulama ───────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.NumericPasswordValidator"
        )
    },
]

# ── Yerelleştirme ─────────────────────────────────────────────────────────────
LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

# ── Statik Dosyalar ───────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ── Medya Dosyaları (PDF'ler vb.) ─────────────────────────────────────────────
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── Varsayılan Birincil Anahtar Tipi ─────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Oturum Yönetimi ───────────────────────────────────────────────────────────
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ── Cache (Redis) ────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    }
}

# ── Celery (Doküman Bölüm 2.1 — Async Görevler) ─────────────────────────────
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL", "redis://localhost:6379/0"
)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Istanbul"

# ── Gemini API ────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ── ChromaDB (Doküman Bölüm 7.2) ─────────────────────────────────────────────
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "/data/chromadb")

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ── Giriş / Çıkış Yönlendirmeleri ────────────────────────────────────────────
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/philosophers/"
LOGOUT_REDIRECT_URL = "/"

# ── Dosya Yükleme Limitleri (Doküman Bölüm 7.4) ─────────────────────────────
# Yalnızca .pdf ve .txt dosyası kabul et, max 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 52_428_800  # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52_428_800  # 50 MB

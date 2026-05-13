# PATH: config/settings/development.py
"""
Agora AI — Geliştirme Ortamı Ayarları
Doküman Bölüm 3.2 (Dizin Yapısı): config/settings/development.py
Sadece yerel geliştirme ortamında kullanılır.
"""

from .base import *  # noqa: F401, F403

# ── Geliştirme Modunu Etkinleştir ────────────────────────────────────────────
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"]

# ── Geliştirme Ortamında Ek Uygulamalar ──────────────────────────────────────
INSTALLED_APPS += [  # noqa: F405
    "django.contrib.admindocs",
]

# ── Email Ayarları (Geliştirmede konsola yaz) ─────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── Django Toolbar (İsteğe bağlı — kurulu değilse çalışır) ──────────────────
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# ── Geliştirme Veritabanı Günlüğü (SQL sorguları konsola) ────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "[{asctime}] {levelname} {name}: {message}"
            ),
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",  # SQL loglamak için "DEBUG" yap
            "propagate": False,
        },
        "agora": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

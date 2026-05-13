# PATH: config/asgi.py
"""
Agora AI — ASGI Konfigürasyonu
Uvicorn ile asenkron istekler için kullanılır.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "config.settings.production"
)

application = get_asgi_application()

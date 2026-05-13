# PATH: config/wsgi.py
"""
Agora AI — WSGI Konfigürasyonu
Gunicorn ile üretim ortamında kullanılır.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "config.settings.production"
)

application = get_wsgi_application()

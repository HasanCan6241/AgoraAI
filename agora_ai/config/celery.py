# PATH: config/celery.py
"""
Agora AI — Celery Konfigürasyonu
Doküman Bölüm 2.1: Async Görevler — Celery + Redis (5.x + 7.x)
Uzun ingestion işlemleri ve arka plan görevleri için kullanılır.
"""

import os

from celery import Celery

# Django ayarlarını Celery'ye bildir
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "config.settings.development"
)

app = Celery("agora_ai")

# Django settings dosyasındaki CELERY_ önekli değerleri kullan
app.config_from_object("django.conf:settings", namespace="CELERY")

# Tüm uygulamaların tasks.py dosyalarını otomatik keşfet
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Celery bağlantısını test etmek için kullanılan görev."""
    print(f"Request: {self.request!r}")

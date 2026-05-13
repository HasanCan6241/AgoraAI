# PATH: config/__init__.py
# Celery uygulamasını Django başlatıldığında yükle.
from .celery import app as celery_app

__all__ = ("celery_app",)

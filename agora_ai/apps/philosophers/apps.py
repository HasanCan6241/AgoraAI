# PATH: apps/philosophers/apps.py
from django.apps import AppConfig


class PhilosophersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.philosophers"
    verbose_name = "Filozoflar"

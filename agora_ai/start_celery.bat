@echo off
set DJANGO_SETTINGS_MODULE=config.settings.development
celery -A config worker -l info --pool=solo
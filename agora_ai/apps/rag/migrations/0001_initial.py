# PATH: apps/rag/migrations/0001_initial.py
"""
Agora AI — RAG App İlk Migration
RAG altyapısı PostgreSQL modeli kullanmaz; ChromaDB'de saklar.
Bu migration yalnızca app'ın kayıtlı olduğunu Django'ya bildirir.
"""

from django.db import migrations


class Migration(migrations.Migration):

    initial = True
    dependencies = []
    operations = []

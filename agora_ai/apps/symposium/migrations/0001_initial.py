# PATH: apps/symposium/migrations/0001_initial.py
"""
Agora AI — Sempozyum İlk Migration
Doküman Bölüm 4.1.6 alanları uygulanmıştır.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("philosophers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SymposiumSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="symposiumsession_set",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="kullanıcı",
                )),
                ("philosophers", models.ManyToManyField(
                    related_name="symposium_sessions",
                    to="philosophers.philosopher",
                    verbose_name="katılımcı filozoflar",
                )),
                ("topic", models.TextField(verbose_name="tartışma konusu")),
                ("zeitgeist_mode", models.CharField(
                    choices=[("classical", "Klasik — Dönemine sadık"), ("modern", "Modern — Çağdaş yorumla")],
                    default="classical",
                    max_length=20,
                    verbose_name="zeitgeist modu",
                )),
                ("rounds_count", models.IntegerField(default=2, verbose_name="tur sayısı")),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Bekliyor"),
                        ("running", "Devam Ediyor"),
                        ("completed", "Tamamlandı"),
                        ("failed", "Başarısız"),
                    ],
                    db_index=True,
                    default="pending",
                    max_length=20,
                    verbose_name="durum",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="oluşturulma tarihi")),
                ("completed_at", models.DateTimeField(blank=True, null=True, verbose_name="tamamlanma tarihi")),
            ],
            options={
                "verbose_name": "sempozyum oturumu",
                "verbose_name_plural": "sempozyum oturumları",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SymposiumTurn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="turns",
                    to="symposium.symposiumsession",
                    verbose_name="sempozyum oturumu",
                )),
                ("philosopher", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="symposium_turns",
                    to="philosophers.philosopher",
                    verbose_name="filozof",
                )),
                ("turn_number", models.IntegerField(verbose_name="tur numarası")),
                ("philosopher_order", models.IntegerField(verbose_name="filozof sırası")),
                ("content", models.TextField(verbose_name="yanıt içeriği")),
                ("rag_chunks_used", models.JSONField(blank=True, default=list, verbose_name="kullanılan RAG chunk'ları")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="oluşturulma tarihi")),
            ],
            options={
                "verbose_name": "sempozyum turu",
                "verbose_name_plural": "sempozyum turları",
                "ordering": ["turn_number", "philosopher_order"],
                "unique_together": {("session", "philosopher", "turn_number")},
            },
        ),
    ]

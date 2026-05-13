# PATH: apps/philosophers/migrations/0001_initial.py
"""
Agora AI — Filozoflar İlk Migration
Doküman Bölüm 4.1.2 ve 4.1.3 alanları uygulanmıştır.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Philosopher",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Filozofun tam adı (ör: 'Immanuel Kant')",
                        max_length=100,
                        verbose_name="tam ad",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="URL dostu isim (ör: 'immanuel-kant').",
                        max_length=100,
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
                (
                    "era",
                    models.CharField(
                        help_text="Yaşadığı dönem (ör: 'Antik Çağ, MÖ 470–399')",
                        max_length=100,
                        verbose_name="dönem",
                    ),
                ),
                (
                    "school",
                    models.CharField(
                        blank=True,
                        help_text="Ait olduğu felsefi akım",
                        max_length=100,
                        verbose_name="felsefi okul",
                    ),
                ),
                (
                    "short_bio",
                    models.TextField(verbose_name="kısa biyografi"),
                ),
                (
                    "long_bio",
                    models.TextField(blank=True, verbose_name="detaylı biyografi"),
                ),
                (
                    "core_concepts",
                    models.JSONField(
                        blank=True,
                        default=list,
                        verbose_name="temel kavramlar",
                    ),
                ),
                (
                    "signature_style",
                    models.TextField(blank=True, verbose_name="imza üslubu"),
                ),
                (
                    "system_prompt_template",
                    models.TextField(verbose_name="sistem prompt şablonu"),
                ),
                (
                    "avatar_image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="philosophers/avatars/",
                        verbose_name="avatar görseli",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="aktif"),
                ),
                (
                    "display_order",
                    models.IntegerField(default=0, verbose_name="sıralama önceliği"),
                ),
            ],
            options={
                "verbose_name": "filozof",
                "verbose_name_plural": "filozoflar",
                "ordering": ["display_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="PhilosophicalWork",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "philosopher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="works",
                        to="philosophers.philosopher",
                        verbose_name="filozof",
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=200, verbose_name="eser başlığı"),
                ),
                (
                    "original_file",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to="philosophical_works/",
                        verbose_name="kaynak dosya",
                    ),
                ),
                (
                    "ingestion_status",
                    models.CharField(
                        choices=[
                            ("pending", "Bekliyor"),
                            ("processing", "İşleniyor"),
                            ("completed", "Tamamlandı"),
                            ("failed", "Başarısız"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                        verbose_name="işleme durumu",
                    ),
                ),
                (
                    "ingestion_error",
                    models.TextField(blank=True, verbose_name="hata mesajı"),
                ),
                (
                    "chunk_count",
                    models.IntegerField(default=0, verbose_name="chunk sayısı"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="yükleme tarihi"
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="tamamlanma tarihi"
                    ),
                ),
            ],
            options={
                "verbose_name": "felsefi eser",
                "verbose_name_plural": "felsefi eserler",
                "ordering": ["philosopher", "title"],
            },
        ),
    ]

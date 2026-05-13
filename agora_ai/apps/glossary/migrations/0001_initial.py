# PATH: apps/glossary/migrations/0001_initial.py
"""Agora AI — Kavram Sözlüğü İlk Migration"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = [("philosophers", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="PhilosophicalConcept",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True, verbose_name="kavram adı")),
                ("slug", models.SlugField(max_length=150, unique=True, verbose_name="slug")),
                ("original_term", models.CharField(blank=True, max_length=150, verbose_name="özgün terim")),
                ("philosophers", models.ManyToManyField(blank=True, related_name="concepts", to="philosophers.philosopher", verbose_name="ilişkili filozoflar")),
                ("short_definition", models.TextField(verbose_name="kısa tanım")),
                ("long_definition", models.TextField(blank=True, verbose_name="ayrıntılı açıklama")),
                ("related_concepts", models.ManyToManyField(blank=True, related_name="_concept_related", symmetrical=True, to="glossary.philosophicalconcept", verbose_name="ilişkili kavramlar")),
                ("is_active", models.BooleanField(default=True, verbose_name="aktif")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="oluşturulma tarihi")),
            ],
            options={
                "verbose_name": "felsefi kavram",
                "verbose_name_plural": "felsefi kavramlar",
                "ordering": ["name"],
            },
        ),
    ]

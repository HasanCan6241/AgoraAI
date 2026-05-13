# PATH: apps/symposium/migrations/0002_dynamic_symposium.py
"""
Agora AI — Sempozyum Dinamik Yapı Migration
Eski rounds_count kaldırılıyor, yeni alanlar ekleniyor.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("symposium", "0001_initial"),
        ("philosophers", "0001_initial"),
    ]

    operations = [
        # Status alanını güncelle
        migrations.AlterField(
            model_name="symposiumsession",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Aktif"),
                    ("completed", "Tamamlandı"),
                    ("failed", "Başarısız"),
                ],
                db_index=True,
                default="active",
                max_length=20,
                verbose_name="durum",
            ),
        ),
        # rounds_count kaldır
        migrations.RemoveField(
            model_name="symposiumsession",
            name="rounds_count",
        ),
        # current_philosopher_index ekle
        migrations.AddField(
            model_name="symposiumsession",
            name="current_philosopher_index",
            field=models.IntegerField(default=0),
        ),

        # ----------------- DÜZELTİLEN KISIM BURASI -----------------
        # ÖNCE UNIQUE TOGETHER KISITLAMASINI KALDIRIYORUZ
        migrations.AlterUniqueTogether(
            name="symposiumturn",
            unique_together=set(),
        ),

        # SONRA ALANLARI SİLİYORUZ
        migrations.RemoveField(
            model_name="symposiumturn",
            name="turn_number",
        ),
        migrations.RemoveField(
            model_name="symposiumturn",
            name="philosopher_order",
        ),
        # -----------------------------------------------------------

        migrations.AddField(
            model_name="symposiumturn",
            name="role",
            field=models.CharField(
                choices=[
                    ("philosopher", "Filozof"),
                    ("user", "Kullanıcı"),
                    ("system", "Sistem"),
                ],
                default="philosopher",
                max_length=20,
                verbose_name="rol",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="symposiumturn",
            name="philosopher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="symposium_turns",
                to="philosophers.philosopher",
            ),
        ),
        migrations.AlterModelOptions(
            name="symposiumturn",
            options={
                "ordering": ["created_at"],
                "verbose_name": "sempozyum turu",
                "verbose_name_plural": "sempozyum turları",
            },
        ),
    ]
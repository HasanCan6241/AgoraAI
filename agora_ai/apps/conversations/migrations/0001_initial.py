# PATH: apps/conversations/migrations/0001_initial.py
"""
Agora AI — Conversations İlk Migration
Doküman Bölüm 4.1.4 ve 4.1.5 alanları uygulanmıştır.
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
            name="ConversationSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="conversationsession_set",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="kullanıcı",
                )),
                ("philosopher", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="conversationsession_set",
                    to="philosophers.philosopher",
                    verbose_name="filozof",
                )),
                ("title", models.CharField(blank=True, max_length=200, verbose_name="sohbet başlığı")),
                ("zeitgeist_mode", models.CharField(
                    choices=[("classical", "Klasik — Dönemine sadık"), ("modern", "Modern — Çağdaş yorumla")],
                    default="classical",
                    max_length=20,
                    verbose_name="zeitgeist modu",
                )),
                ("context_summary", models.TextField(blank=True, verbose_name="bağlam özeti")),
                ("is_active", models.BooleanField(default=True, verbose_name="aktif")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="başlangıç tarihi")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="son güncelleme")),
            ],
            options={
                "verbose_name": "sohbet oturumu",
                "verbose_name_plural": "sohbet oturumları",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="messages",
                    to="conversations.conversationsession",
                    verbose_name="oturum",
                )),
                ("role", models.CharField(
                    choices=[("user", "Kullanıcı"), ("assistant", "Asistan (Filozof)")],
                    db_index=True,
                    max_length=20,
                    verbose_name="rol",
                )),
                ("content", models.TextField(verbose_name="içerik")),
                ("rag_chunks_used", models.JSONField(blank=True, default=list, verbose_name="kullanılan RAG chunk'ları")),
                ("token_count", models.IntegerField(default=0, verbose_name="token sayısı")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="oluşturulma tarihi")),
            ],
            options={
                "verbose_name": "mesaj",
                "verbose_name_plural": "mesajlar",
                "ordering": ["created_at"],
            },
        ),
    ]

# PATH: apps/accounts/migrations/0001_initial.py
"""
Agora AI — CustomUser İlk Migration
Doküman Bölüm 4.1.1 alanları birebir uygulanmıştır.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomUser",
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
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Designates that this user has all permissions "
                            "without explicitly assigning them."
                        ),
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        max_length=254,
                        unique=True,
                        verbose_name="e-posta adresi",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        help_text="Platformda görünen ad. En fazla 50 karakter.",
                        max_length=50,
                        unique=True,
                        verbose_name="kullanıcı adı",
                    ),
                ),
                (
                    "preferred_language",
                    models.CharField(
                        choices=[
                            ("tr", "Türkçe"),
                            ("en", "English"),
                            ("de", "Deutsch"),
                            ("fr", "Français"),
                        ],
                        default="tr",
                        max_length=10,
                        verbose_name="tercih edilen dil",
                    ),
                ),
                (
                    "zeitgeist_mode",
                    models.CharField(
                        choices=[
                            ("classical", "Klasik — Dönemine sadık"),
                            ("modern", "Modern — Çağdaş yorumla"),
                        ],
                        default="classical",
                        max_length=20,
                        verbose_name="zeitgeist modu",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="kayıt tarihi",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        verbose_name="aktif",
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        verbose_name="personel",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text=(
                            "The groups this user belongs to. A user will get "
                            "all permissions granted to each of their groups."
                        ),
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "kullanıcı",
                "verbose_name_plural": "kullanıcılar",
                "ordering": ["-created_at"],
            },
        ),
    ]

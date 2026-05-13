# PATH: apps/accounts/admin.py
"""
Agora AI — Kullanıcı Admin Paneli Kaydı
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """CustomUser için zenginleştirilmiş admin görünümü."""

    model = CustomUser
    list_display = [
        "email",
        "username",
        "preferred_language",
        "zeitgeist_mode",
        "is_active",
        "is_staff",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "is_staff",
        "preferred_language",
        "zeitgeist_mode",
    ]
    search_fields = ["email", "username"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "last_login"]

    # Detay sayfası alanları
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (
            _("Tercihler"),
            {
                "fields": ("preferred_language", "zeitgeist_mode"),
            },
        ),
        (
            _("İzinler"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Önemli Tarihler"),
            {"fields": ("last_login", "created_at")},
        ),
    )

    # Yeni kullanıcı oluşturma sayfası alanları
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "preferred_language",
                    "zeitgeist_mode",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

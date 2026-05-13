# PATH: apps/conversations/admin.py
"""
Agora AI — Sohbet Admin Paneli
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import ConversationSession, Message


class MessageInline(admin.TabularInline):
    """Oturuma ait mesajlar — satır içi."""

    model = Message
    extra = 0
    readonly_fields = ["role", "content_preview", "token_count", "created_at"]
    fields = ["role", "content_preview", "token_count", "created_at"]
    max_num = 0  # Inline'dan yeni mesaj eklenemez
    can_delete = False

    def content_preview(self, obj):
        return obj.content[:120] + "..." if len(obj.content) > 120 else obj.content

    content_preview.short_description = _("İçerik")


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "philosopher",
        "title_short",
        "zeitgeist_mode",
        "message_count_display",
        "is_active",
        "updated_at",
    ]
    list_filter = ["is_active", "zeitgeist_mode", "philosopher"]
    search_fields = ["user__email", "user__username", "philosopher__name", "title"]
    readonly_fields = ["created_at", "updated_at", "context_summary"]
    ordering = ["-updated_at"]
    inlines = [MessageInline]

    def title_short(self, obj):
        return obj.title[:60] if obj.title else "—"

    title_short.short_description = _("Başlık")

    def message_count_display(self, obj):
        count = obj.get_message_count()
        return format_html("<strong>{}</strong> mesaj", count)

    message_count_display.short_description = _("Mesaj")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "role", "content_preview", "token_count", "created_at"]
    list_filter = ["role"]
    search_fields = ["content", "session__user__username"]
    readonly_fields = ["created_at", "rag_chunks_used"]
    ordering = ["-created_at"]

    def content_preview(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content

    content_preview.short_description = _("İçerik")

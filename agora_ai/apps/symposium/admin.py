# PATH: apps/symposium/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import SymposiumSession, SymposiumTurn


class SymposiumTurnInline(admin.TabularInline):
    model = SymposiumTurn
    extra = 0
    readonly_fields = ["philosopher", "role", "content_preview", "created_at"]
    fields = ["philosopher", "role", "content_preview", "created_at"]
    can_delete = False
    max_num = 0

    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = _("İçerik")


@admin.register(SymposiumSession)
class SymposiumSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "topic_short", "philosopher_names",
        "status_badge", "turn_count", "created_at",
    ]
    list_filter   = ["status", "zeitgeist_mode"]
    search_fields = ["user__username", "topic"]
    readonly_fields = [
        "created_at",
        "current_philosopher_index",
    ]
    # ↑ "status" ve "completed_at" artık readonly değil — admin düzenleyebilir

    ordering = ["-created_at"]
    inlines  = [SymposiumTurnInline]
    actions  = ["reactivate_sessions"]  # ← list action

    # --- List Action ---
    @admin.action(description=_("Seçili sempozyumları tekrar aktif yap"))
    def reactivate_sessions(self, request, queryset):
        count = 0
        for session in queryset:
            session.reactivate()
            count += 1
        self.message_user(
            request,
            _(f"{count} sempozyum oturumu tekrar aktif hale getirildi."),
        )

    # --- Detail sayfasında da buton ---
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj and not obj.is_active:
            extra_context["show_reactivate"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    # --- Display helpers ---
    def topic_short(self, obj):
        return obj.topic[:60] + "..." if len(obj.topic) > 60 else obj.topic
    topic_short.short_description = _("Konu")

    def philosopher_names(self, obj):
        return ", ".join(p.name for p in obj.philosophers.all())
    philosopher_names.short_description = _("Filozoflar")

    def turn_count(self, obj):
        return obj.turn_count
    turn_count.short_description = _("Tur")

    def status_badge(self, obj):
        colors = {
            "active":    ("#ffc107", "#000"),
            "completed": ("#198754", "#fff"),
            "failed":    ("#dc3545", "#fff"),
        }
        bg, fg = colors.get(obj.status, ("#6c757d", "#fff"))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:4px;font-size:0.8rem;font-weight:600;">{}</span>',
            bg, fg, obj.get_status_display(),
        )
    status_badge.short_description = _("Durum")


@admin.register(SymposiumTurn)
class SymposiumTurnAdmin(admin.ModelAdmin):
    list_display  = [
        "id", "session", "philosopher", "role",
        "content_preview", "created_at",
    ]
    list_filter   = ["role", "philosopher"]
    search_fields = ["content", "philosopher__name"]
    readonly_fields = ["created_at", "rag_chunks_used"]

    def content_preview(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    content_preview.short_description = _("İçerik")
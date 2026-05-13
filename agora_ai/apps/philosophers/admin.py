# PATH: apps/philosophers/admin.py
"""
Agora AI — Filozoflar Admin Paneli
Doküman Bölüm 6/AŞAMA 3: Admin paneline kaydet, zengin list_display tanımla.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Philosopher, PhilosophicalWork


class PhilosopherModeInline(admin.TabularInline):
    """Philosopher detay sayfasında mod listesi."""
    from apps.philosophers.models import PhilosopherMode
    model = PhilosopherMode
    extra = 1
    fields = [
        "mode_key", "display_name", "button_label",
        "button_description", "is_default", "is_active", "display_order",
    ]

class PhilosophicalWorkInline(admin.TabularInline):
    """Filozofun eserleri — Philosopher detay sayfasında satır içi."""

    model = PhilosophicalWork
    extra = 1
    fields = [
        "title",
        "original_file",
        "ingestion_status",
        "chunk_count",
        "created_at",
        "completed_at",
    ]
    readonly_fields = ["ingestion_status", "chunk_count", "created_at", "completed_at"]
    show_change_link = True


@admin.register(Philosopher)
class PhilosopherAdmin(admin.ModelAdmin):
    """Filozof yönetim paneli."""

    list_display = [
        "name",
        "era",
        "school",
        "work_count_display",
        "is_active",
        "display_order",
        "avatar_preview",
    ]
    list_filter = ["is_active", "era"]
    search_fields = ["name", "era", "school", "short_bio"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["display_order", "name"]
    list_editable = ["is_active", "display_order"]
    inlines = [PhilosopherModeInline, PhilosophicalWorkInline]

    fieldsets = (
        (
            _("Temel Bilgiler"),
            {
                "fields": (
                    "name",
                    "slug",
                    "era",
                    "school",
                    "avatar_image",
                    "is_active",
                    "display_order",
                )
            },
        ),
        (
            _("Biyografi"),
            {
                "fields": ("short_bio", "long_bio"),
            },
        ),
        (
            _("Felsefi İçerik"),
            {
                "fields": ("core_concepts", "signature_style"),
                "description": _(
                    "core_concepts JSON dizisi olarak girilmeli: "
                    '["Kavram1", "Kavram2"]'
                ),
            },
        ),
        (
            _("LLM Persona Şablonu"),
            {
                "fields": ("system_prompt_template",),
                "classes": ("collapse",),
                "description": _(
                    "Doküman Bölüm 7.1 — Yer tutucular: "
                    "{philosopher_name}, {era}, {core_concepts}, "
                    "{signature_style}, {zeitgeist_block}, "
                    "{rag_context}, {context_summary}"
                ),
            },
        ),
    )

    def work_count_display(self, obj):
        """Tamamlanan eser sayısını renkli rozet ile göster."""
        count = obj.work_count
        color = "#198754" if count > 0 else "#6c757d"
        return format_html(
            '<span style="color: {}; font-weight: 600;">{} eser</span>',
            color,
            count,
        )

    work_count_display.short_description = _("RAG Eserler")

    def avatar_preview(self, obj):
        """Küçük avatar önizlemesi."""
        if obj.avatar_image:
            return format_html(
                '<img src="{}" style="width:40px; height:40px; '
                "border-radius:50%; object-fit:cover;\">",
                obj.avatar_image.url,
            )
        return format_html(
            '<span style="color: #6c757d; font-size: 0.8rem;">—</span>'
        )

    avatar_preview.short_description = _("Avatar")


@admin.register(PhilosophicalWork)
class PhilosophicalWorkAdmin(admin.ModelAdmin):
    """Felsefi Eser yönetim paneli."""

    list_display = [
        "title",
        "philosopher",
        "ingestion_status_badge",
        "chunk_count",
        "created_at",
        "completed_at",
    ]
    list_filter = ["ingestion_status", "philosopher"]
    search_fields = ["title", "philosopher__name"]
    readonly_fields = [
        "ingestion_status",
        "ingestion_error",
        "chunk_count",
        "created_at",
        "completed_at",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            _("Eser Bilgileri"),
            {"fields": ("philosopher", "title", "original_file")},
        ),
        (
            _("İşleme Durumu"),
            {
                "fields": (
                    "ingestion_status",
                    "chunk_count",
                    "ingestion_error",
                    "created_at",
                    "completed_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def ingestion_status_badge(self, obj):
        """İşleme durumunu renkli rozet ile göster."""
        colors = {
            "pending":    ("#ffc107", "#000"),
            "processing": ("#0dcaf0", "#000"),
            "completed":  ("#198754", "#fff"),
            "failed":     ("#dc3545", "#fff"),
        }
        bg, fg = colors.get(obj.ingestion_status, ("#6c757d", "#fff"))
        return format_html(
            '<span style="background:{}; color:{}; padding:2px 8px; '
            "border-radius:4px; font-size:0.8rem; font-weight:600;\">{}</span>",
            bg,
            fg,
            obj.get_ingestion_status_display(),
        )

    ingestion_status_badge.short_description = _("Durum")

    actions = ["reprocess_selected_works"]

    def save_model(self, request, obj, form, change):
        """
        Dosya uzantısını doğrula (Doküman Bölüm 7.4).
        Yeni yükleme varsa ingestion_status'u 'pending' sıfırla
        ve Celery görevini tetikle (Doküman Bölüm 4.2 / AŞAMA 4).
        """
        obj.validate_file_extension()
        if not change and obj.original_file:
            obj.ingestion_status = PhilosophicalWork.STATUS_PENDING
        elif change and "original_file" in form.changed_data:
            obj.ingestion_status = PhilosophicalWork.STATUS_PENDING
            obj.ingestion_error = ""
            obj.chunk_count = 0
        super().save_model(request, obj, form, change)
        try:
            from apps.rag.admin import trigger_ingestion_for_work
            trigger_ingestion_for_work(obj)
        except Exception:
            pass  # Celery çalışmıyorsa admin yine de çalışmaya devam eder

    @admin.action(description="Seçili eserleri RAG'a yeniden işle (Celery)")
    def reprocess_selected_works(self, request, queryset):
        """Seçili PhilosophicalWork'leri ingestion kuyruğuna alır."""
        from apps.rag.tasks import ingest_philosophical_work
        count = 0
        for work in queryset:
            if work.original_file:
                work.ingestion_status = PhilosophicalWork.STATUS_PENDING
                work.ingestion_error = ""
                work.save(update_fields=["ingestion_status", "ingestion_error"])
                ingest_philosophical_work.delay(work.pk)
                count += 1
        self.message_user(
            request, f"{count} eser kuyruğa alındı.", level="success"
        )

from apps.philosophers.models import PhilosopherMode

@admin.register(PhilosopherMode)
class PhilosopherModeAdmin(admin.ModelAdmin):
    list_display  = [
        "philosopher", "mode_key", "display_name",
        "is_default", "is_active", "display_order",
    ]
    list_filter   = ["philosopher", "is_active", "is_default"]
    search_fields = ["philosopher__name", "mode_key", "display_name"]
    list_editable = ["is_default", "is_active", "display_order"]
    fieldsets = (
        (None, {
            "fields": (
                "philosopher", "mode_key", "display_name",
                "button_label", "button_description",
                "is_default", "is_active", "display_order",
            )
        }),
        ("Sistem Promptu", {
            "fields": ("system_prompt",),
            "classes": ("wide",),
            "description": (
                "Yer tutucular: {zeitgeist_block}, "
                "{rag_context}, {context_summary}"
            ),
        }),
    )
# PATH: apps/rag/admin.py
"""
Agora AI — RAG Admin Aksiyonları
Doküman Bölüm 6/AŞAMA 4: Admin panelinden ingestion tetikleme.

PhilosophicalWorkAdmin, philosophers/admin.py'dedir.
Bu dosya Celery görevlerini tetikleyen admin aksiyonlarını register eder.
"""

from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _


# PhilosophersAdmin'i extend eden signal hook: eser kaydedilince görevi tetikle
# Bu fonksiyon philosophers/admin.py'deki save_model'dan çağrılır
def trigger_ingestion_for_work(work) -> None:
    """
    PhilosophicalWork kaydedildiğinde Celery ingestion görevini tetikler.
    philosophers/admin.py → save_model() → bu fonksiyon.

    Args:
        work: PhilosophicalWork instance.
    """
    from apps.rag.tasks import ingest_philosophical_work

    if work.original_file and work.ingestion_status in (
        work.STATUS_PENDING,
        work.STATUS_FAILED,
    ):
        ingest_philosophical_work.delay(work.pk)


# ── Admin Aksiyon: Seçili eserleri yeniden işle ────────────────────────────
@admin.action(description=_("Seçili eserleri RAG'a yeniden işle (Celery)"))
def reprocess_selected_works(modeladmin, request, queryset):
    """
    Admin panelinde seçili PhilosophicalWork'leri yeniden ingestion kuyruğuna alır.
    """
    from apps.rag.tasks import ingest_philosophical_work

    count = 0
    for work in queryset:
        if work.original_file:
            work.ingestion_status = work.STATUS_PENDING
            work.ingestion_error = ""
            work.save(update_fields=["ingestion_status", "ingestion_error"])
            ingest_philosophical_work.delay(work.pk)
            count += 1

    modeladmin.message_user(
        request,
        _(f"{count} eser Celery kuyruğuna alındı."),
        messages.SUCCESS,
    )


@admin.action(description=_("Seçili filozofların ChromaDB collection'ını sil"))
def delete_philosopher_collections(modeladmin, request, queryset):
    """
    Admin panelinde seçili Philosopher'ların ChromaDB verilerini temizler.
    """
    from apps.rag.services.chroma_store import delete_philosopher_collection

    count = 0
    for philosopher in queryset:
        if delete_philosopher_collection(philosopher.pk):
            count += 1

    modeladmin.message_user(
        request,
        _(f"{count} filozofun ChromaDB collection'ı silindi."),
        messages.WARNING,
    )

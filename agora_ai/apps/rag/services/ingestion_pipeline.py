# PATH: apps/rag/services/ingestion_pipeline.py
"""
Agora AI — RAG Ingestion Pipeline (Orkestratör)
Doküman Bölüm 4.2 (RAG Pipeline) referans alınmıştır.

Akış (Doküman Bölüm 4.2):
    PhilosophicalWork → extract_text() → chunk_text()
    → ingest_chunks() → work.ingestion_status = "completed"

Bu modül hem Celery task (tasks.py) hem de
admin panel aksiyonu tarafından çağrılır.
"""

import logging
from typing import Tuple

from django.utils import timezone

logger = logging.getLogger("agora.rag.pipeline")


def run_ingestion(work_id: int) -> Tuple[bool, str]:
    """
    Tek bir PhilosophicalWork için tam ingestion pipeline'ını çalıştırır.
    Doküman Bölüm 4.2 ve 7.2 akışı:

        pending → processing → completed
                             → failed (hata durumunda)

    Django ORM import'ları fonksiyon içinde yapılır; Celery worker
    Django'yu doğru başlatmadan önce import hatası almayı önler.

    Args:
        work_id: PhilosophicalWork.pk

    Returns:
        (success: bool, message: str) — sonuç ve açıklama.
    """
    # ── Import'lar (Django ORM hazır olduktan sonra) ──────────────────────
    from apps.philosophers.models import PhilosophicalWork
    from apps.rag.services.chroma_store import delete_work_chunks, ingest_chunks
    from apps.rag.services.pdf_extractor import chunk_text, extract_text

    # ── 1. Eseri veritabanından çek ──────────────────────────────────────
    try:
        work = PhilosophicalWork.objects.select_related("philosopher").get(
            pk=work_id
        )
    except PhilosophicalWork.DoesNotExist:
        msg = f"PhilosophicalWork bulunamadı: id={work_id}"
        logger.error(msg)
        return False, msg

    philosopher_id = work.philosopher.pk
    work_title = work.title

    logger.info(
        "Ingestion başladı: work_id=%d, '%s' (philosopher=%s)",
        work_id,
        work_title,
        work.philosopher.name,
    )

    # ── 2. Durumu 'processing' olarak işaretle ───────────────────────────
    work.ingestion_status = PhilosophicalWork.STATUS_PROCESSING
    work.ingestion_error = ""
    work.chunk_count = 0
    work.save(
        update_fields=["ingestion_status", "ingestion_error", "chunk_count"]
    )

    # ── 3. Dosya varlık kontrolü ─────────────────────────────────────────
    if not work.original_file:
        msg = f"Dosya yüklenmemiş: work_id={work_id}"
        _mark_failed(work, msg)
        return False, msg

    file_path = work.original_file.path

    try:
        # ── 4. Metin çıkar (PDF veya TXT) ─────────────────────────────
        raw_text = extract_text(file_path)

        if not raw_text.strip():
            msg = f"Dosyadan metin çıkarılamadı (boş içerik): {file_path}"
            _mark_failed(work, msg)
            return False, msg

        # ── 5. Chunk'lara böl ─────────────────────────────────────────
        chunks = chunk_text(raw_text)

        if not chunks:
            msg = f"Chunklama sonuç vermedi: work_id={work_id}"
            _mark_failed(work, msg)
            return False, msg

        logger.info(
            "Chunklama tamamlandı: work_id=%d, %d chunk",
            work_id,
            len(chunks),
        )

        # ── 6. Eski chunk'ları sil (yeniden işleme durumu için) ───────
        delete_work_chunks(philosopher_id=philosopher_id, work_id=work_id)

        # ── 7. ChromaDB'ye kaydet ─────────────────────────────────────
        saved_count = ingest_chunks(
            philosopher_id=philosopher_id,
            work_id=work_id,
            chunks=chunks,
        )

        # ── 8. Başarı: durumu 'completed' olarak güncelle ─────────────
        work.ingestion_status = PhilosophicalWork.STATUS_COMPLETED
        work.chunk_count = saved_count
        work.completed_at = timezone.now()
        work.ingestion_error = ""
        work.save(
            update_fields=[
                "ingestion_status",
                "chunk_count",
                "completed_at",
                "ingestion_error",
            ]
        )

        success_msg = (
            f"'{work_title}' başarıyla işlendi: "
            f"{saved_count} chunk ChromaDB'ye kaydedildi."
        )
        logger.info("Ingestion başarılı: work_id=%d — %s", work_id, success_msg)
        return True, success_msg

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error(
            "Ingestion başarısız: work_id=%d — %s",
            work_id,
            error_msg,
            exc_info=True,
        )
        _mark_failed(work, error_msg)
        return False, error_msg


def _mark_failed(work, error_message: str) -> None:
    """
    PhilosophicalWork'ün durumunu 'failed' olarak işaretle.
    Hata mesajını ingestion_error alanına kaydet.
    """
    from apps.philosophers.models import PhilosophicalWork

    work.ingestion_status = PhilosophicalWork.STATUS_FAILED
    work.ingestion_error = error_message[:2000]  # Alan uzunluk sınırı
    work.save(update_fields=["ingestion_status", "ingestion_error"])
    logger.warning(
        "Ingestion FAILED işaretlendi: work_id=%d — %s",
        work.pk,
        error_message,
    )

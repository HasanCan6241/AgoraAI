# PATH: apps/rag/tasks.py
"""
Agora AI — RAG Celery Görevleri
Doküman Bölüm 2.1 (Celery + Redis) ve Bölüm 6/AŞAMA 4 referans alınmıştır.

Görevler:
    ingest_philosophical_work  — Tek bir eseri arka planda işle
    ingest_all_pending_works   — Tüm 'pending' eserleri toplu işle
    retry_failed_works         — 'failed' eserleri yeniden dene
"""

import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger("agora.rag.tasks")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,        # 60 saniye sonra yeniden dene
    acks_late=True,                 # Görev tamamlandıktan sonra acknowledge et
    time_limit=600,                 # Maksimum 10 dakika
    soft_time_limit=540,           # 9 dakikada soft uyarı
    name="rag.ingest_philosophical_work",
)
def ingest_philosophical_work(self, work_id: int) -> dict:
    """
    Tek bir PhilosophicalWork'ü Celery worker'da işler.
    Doküman Bölüm 4.2 akışı: extract → chunk → embed → store

    Admin panelinden save_model() veya toplu işlem sırasında tetiklenir.

    Args:
        work_id: PhilosophicalWork.pk

    Returns:
        {"success": bool, "work_id": int, "message": str}
    """
    from apps.rag.services.ingestion_pipeline import run_ingestion

    logger.info(
        "Celery görev başladı: ingest_philosophical_work(work_id=%d) — "
        "deneme %d/%d",
        work_id,
        self.request.retries + 1,
        self.max_retries + 1,
    )

    try:
        success, message = run_ingestion(work_id=work_id)

        result = {
            "success": success,
            "work_id": work_id,
            "message": message,
        }

        if success:
            logger.info(
                "Celery görev BAŞARILI: work_id=%d — %s", work_id, message
            )
        else:
            logger.warning(
                "Celery görev BAŞARISIZ: work_id=%d — %s", work_id, message
            )

        return result

    except Exception as exc:
        logger.error(
            "Celery görev HATA: work_id=%d — %s",
            work_id,
            exc,
            exc_info=True,
        )
        # max_retries'a ulaşılmadıysa yeniden kuyruğa al
        raise self.retry(exc=exc)


@shared_task(
    name="rag.ingest_all_pending_works",
    time_limit=3600,  # 1 saat
)
def ingest_all_pending_works() -> dict:
    """
    Veritabanındaki tüm 'pending' durumundaki eserleri kuyruğa alır.
    Admin panel üzerinden veya management command'dan tetiklenebilir.

    Returns:
        {"queued": int, "work_ids": list}
    """
    from apps.philosophers.models import PhilosophicalWork

    pending_works = PhilosophicalWork.objects.filter(
        ingestion_status=PhilosophicalWork.STATUS_PENDING,
        original_file__isnull=False,
    ).exclude(original_file="")

    queued_ids = []
    for work in pending_works:
        # Her eser için ayrı görev kuyruğa al
        ingest_philosophical_work.delay(work.pk)
        queued_ids.append(work.pk)
        logger.info("Kuyruğa alındı: work_id=%d ('%s')", work.pk, work.title)

    result = {"queued": len(queued_ids), "work_ids": queued_ids}
    logger.info(
        "ingest_all_pending_works: %d eser kuyruğa alındı", len(queued_ids)
    )
    return result


@shared_task(
    name="rag.retry_failed_works",
    time_limit=3600,
)
def retry_failed_works() -> dict:
    """
    'failed' durumundaki eserleri 'pending' olarak sıfırlar ve yeniden kuyruğa alır.

    Returns:
        {"retried": int, "work_ids": list}
    """
    from apps.philosophers.models import PhilosophicalWork

    failed_works = PhilosophicalWork.objects.filter(
        ingestion_status=PhilosophicalWork.STATUS_FAILED,
        original_file__isnull=False,
    ).exclude(original_file="")

    retried_ids = []
    with transaction.atomic():
        for work in failed_works:
            work.ingestion_status = PhilosophicalWork.STATUS_PENDING
            work.ingestion_error = ""
            work.save(update_fields=["ingestion_status", "ingestion_error"])
            ingest_philosophical_work.delay(work.pk)
            retried_ids.append(work.pk)
            logger.info(
                "Yeniden deneniyor: work_id=%d ('%s')", work.pk, work.title
            )

    result = {"retried": len(retried_ids), "work_ids": retried_ids}
    logger.info(
        "retry_failed_works: %d eser yeniden kuyruğa alındı", len(retried_ids)
    )
    return result

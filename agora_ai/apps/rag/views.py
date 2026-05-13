# PATH: apps/rag/views.py
"""
Agora AI — RAG Görünümleri
Doküman Bölüm 6/AŞAMA 4:
    - /rag/status/<work_id>/   → Ingestion durum sorgusu (JSON API)
    - /rag/upload/<phil_slug>/ → Admin dışından eser yükleme
    - /rag/stats/<phil_slug>/  → Filozof ChromaDB istatistikleri (JSON)
Tüm view'lar @login_required ve is_staff kontrolüyle korunur.
"""

import json
import logging
import os

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.philosophers.models import Philosopher, PhilosophicalWork

logger = logging.getLogger("agora.rag.views")


@login_required
@require_http_methods(["GET"])
def ingestion_status(request, work_id: int):
    """
    Doküman Bölüm 6/AŞAMA 4: Ingestion durum sorgusu (polling için JSON API).
    Frontend (Admin + AŞAMA 6 şablonları) bu endpoint'i yoklayabilir.

    GET /rag/status/<work_id>/
    Yanıt: {"work_id", "status", "chunk_count", "error", "is_ready"}
    """
    if not request.user.is_staff:
        return JsonResponse({"error": "Yetkisiz erişim."}, status=403)

    work = get_object_or_404(PhilosophicalWork, pk=work_id)

    return JsonResponse(
        {
            "work_id": work.pk,
            "title": work.title,
            "philosopher": work.philosopher.name,
            "status": work.ingestion_status,
            "status_display": work.get_ingestion_status_display(),
            "chunk_count": work.chunk_count,
            "error": work.ingestion_error or None,
            "is_ready": work.is_ready,
            "completed_at": (
                work.completed_at.isoformat() if work.completed_at else None
            ),
        }
    )


@login_required
@require_http_methods(["GET", "POST"])
def upload_work(request, philosopher_slug: str):
    """
    Admin dışı eser yükleme endpoint'i.
    Doküman Bölüm 7.4: Yalnızca .pdf ve .txt, max 50MB.
    Yükleme sonrası Celery ingestion görevi tetiklenir.

    POST: {"title": str, "file": PDF/TXT}
    """
    if not request.user.is_staff:
        return JsonResponse({"error": "Yalnızca personel yükleyebilir."}, status=403)

    philosopher = get_object_or_404(
        Philosopher, slug=philosopher_slug, is_active=True
    )

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        uploaded_file = request.FILES.get("file")

        # Doğrulama
        errors = {}
        if not title:
            errors["title"] = "Eser başlığı zorunludur."
        if not uploaded_file:
            errors["file"] = "Dosya seçilmedi."
        else:
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext not in (".pdf", ".txt"):
                errors["file"] = "Yalnızca .pdf ve .txt dosyaları kabul edilir."
            if uploaded_file.size > 52_428_800:  # 50 MB
                errors["file"] = "Dosya boyutu 50 MB'ı aşıyor."

        if errors:
            return JsonResponse({"errors": errors}, status=400)

        # Eseri oluştur
        work = PhilosophicalWork.objects.create(
            philosopher=philosopher,
            title=title,
            original_file=uploaded_file,
            ingestion_status=PhilosophicalWork.STATUS_PENDING,
        )

        # Celery görevi tetikle
        try:
            from apps.rag.tasks import ingest_philosophical_work
            ingest_philosophical_work.delay(work.pk)
            logger.info(
                "Eser yüklendi ve kuyruğa alındı: work_id=%d ('%s')",
                work.pk,
                work.title,
            )
        except Exception as exc:
            logger.error("Celery tetiklenemedi: %s", exc)

        return JsonResponse(
            {
                "success": True,
                "work_id": work.pk,
                "title": work.title,
                "status": work.ingestion_status,
                "message": "Eser yüklendi, arka planda işleniyor.",
            },
            status=201,
        )

    # GET: Yükleme formu
    existing_works = philosopher.works.all().order_by("-created_at")
    return render(
        request,
        "rag/upload_work.html",
        {
            "philosopher": philosopher,
            "existing_works": existing_works,
        },
    )


@login_required
@require_http_methods(["GET"])
def chroma_stats(request, philosopher_slug: str):
    """
    Filozof için ChromaDB collection istatistiklerini döndürür.
    Debug ve admin izleme için kullanılır.

    GET /rag/stats/<philosopher_slug>/
    Yanıt: {"philosopher", "collection_name", "chunk_count", "exists"}
    """
    if not request.user.is_staff:
        return JsonResponse({"error": "Yetkisiz erişim."}, status=403)

    philosopher = get_object_or_404(Philosopher, slug=philosopher_slug)

    from apps.rag.services.chroma_store import get_collection_stats

    stats = get_collection_stats(philosopher.pk)
    stats["philosopher"] = philosopher.name
    stats["philosopher_slug"] = philosopher.slug

    return JsonResponse(stats)

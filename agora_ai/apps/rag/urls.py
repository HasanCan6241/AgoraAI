# PATH: apps/rag/urls.py
"""
Agora AI — RAG URL Yönlendirmeleri
Doküman Bölüm 6/AŞAMA 4: Ingestion durum API, yükleme, istatistik.
"""

from django.urls import path

from . import views

app_name = "rag"

urlpatterns = [
    # Ingestion durum sorgusu (polling JSON API)
    path(
        "status/<int:work_id>/",
        views.ingestion_status,
        name="status",
    ),
    # Eser yükleme (admin dışı)
    path(
        "upload/<slug:philosopher_slug>/",
        views.upload_work,
        name="upload",
    ),
    # ChromaDB collection istatistikleri
    path(
        "stats/<slug:philosopher_slug>/",
        views.chroma_stats,
        name="stats",
    ),
]

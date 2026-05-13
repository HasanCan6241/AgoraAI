# PATH: apps/rag/services/__init__.py
"""
Agora AI — RAG Servis Paketi
Public API — diğer app'lar bu importları kullanır.
"""

from .chroma_store import (
    delete_philosopher_collection,
    delete_work_chunks,
    get_collection_stats,
    ingest_chunks,
    query_chunks,
)
from .ingestion_pipeline import run_ingestion
from .pdf_extractor import chunk_text, extract_text

__all__ = [
    "extract_text",
    "chunk_text",
    "ingest_chunks",
    "query_chunks",
    "delete_philosopher_collection",
    "delete_work_chunks",
    "get_collection_stats",
    "run_ingestion",
]

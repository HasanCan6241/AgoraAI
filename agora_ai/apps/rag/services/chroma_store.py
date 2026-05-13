# PATH: apps/rag/services/chroma_store.py
"""
Agora AI — ChromaDB Vektör Deposu
Doküman Bölüm 4.2 (RAG Pipeline) ve 7.2 (ChromaDB konfigürasyonu) referans alınmıştır.

Sorumluluklar:
    - ChromaDB persistent client'ı başlat (singleton pattern)
    - Philosopher başına ayrı collection aç/oluştur
    - Chunk'ları embed edip ChromaDB'ye kaydet (ingest_chunks)
    - Sorgu zamanı en yakın N chunk'ı getir (query_chunks)
    - Philosopher collection'ını sil (delete_philosopher_collection)

Doküman Bölüm 7.2:
    - Collection adı: f"philosopher_{philosopher_id}"
    - Embedding modeli: ChromaDB'nin varsayılan (all-MiniLM-L6-v2)
    - n_results: 5
    - CHROMA_PERSIST_DIR: .env → settings.CHROMA_PERSIST_DIR
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agora.rag.chroma")

# ChromaDB client — modül düzeyinde singleton
_chroma_client = None


def _get_client():
    """
    ChromaDB persistent client'ı döndürür.
    İlk çağrıda başlatır; sonraki çağrılarda önbellekteki nesneyi kullanır.
    Doküman Bölüm 7.2: settings.CHROMA_PERSIST_DIR kullanılır.
    """
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    try:
        import chromadb
        from django.conf import settings

        persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", "/data/chromadb")
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
        logger.info("ChromaDB client başlatıldı: %s", persist_dir)
    except ImportError as exc:
        raise RuntimeError(
            "chromadb kurulu değil. `pip install chromadb` komutunu çalıştırın."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"ChromaDB başlatılamadı: {exc}") from exc

    return _chroma_client


def _collection_name(philosopher_id: int) -> str:
    """
    Doküman Bölüm 7.2: Collection adı → f"philosopher_{philosopher_id}"
    """
    return f"philosopher_{philosopher_id}"


def get_or_create_collection(philosopher_id: int):
    """
    Verilen filozofa ait ChromaDB collection'ını açar ya da oluşturur.

    Args:
        philosopher_id: Philosopher model pk'si.

    Returns:
        chromadb.Collection nesnesi.
    """
    client = _get_client()
    name = _collection_name(philosopher_id)
    try:
        from chromadb.utils import embedding_functions

        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-mpnet-base-v2"
        )

        collection = client.get_or_create_collection(
            name=name,
            embedding_function=embedding_fn,
            metadata={"philosopher_id": philosopher_id},
        )
        return collection
    except Exception as exc:
        raise RuntimeError(
            f"Collection oluşturulamadı (philosopher_id={philosopher_id}): {exc}"
        ) from exc


def ingest_chunks(
    philosopher_id: int,
    work_id: int,
    chunks: List[str],
) -> int:
    """
    Chunk listesini ChromaDB'ye embed ederek kaydeder.
    Doküman Bölüm 4.2 ve 7.2: Her chunk için benzersiz ID üretilir.

    Args:
        philosopher_id: Philosopher.pk — hangi collection'a yazılacak.
        work_id:        PhilosophicalWork.pk — metadata olarak saklanır.
        chunks:         Metin parçaları listesi.

    Returns:
        Başarıyla kaydedilen chunk sayısı.

    Raises:
        RuntimeError: ChromaDB yazma hatası.
    """
    if not chunks:
        logger.warning(
            "ingest_chunks: Boş chunk listesi (philosopher=%d, work=%d)",
            philosopher_id,
            work_id,
        )
        return 0

    collection = get_or_create_collection(philosopher_id)

    # ChromaDB'nin ID'leri benzersiz olmalı; uuid4 kullan
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "philosopher_id": philosopher_id,
            "work_id": work_id,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    # Büyük batch'leri 100'er chunk'lık parçalar halinde gönder (OOM'u önler)
    batch_size = 100
    ingested = 0

    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        batch_ids = ids[start:end]
        batch_docs = chunks[start:end]
        batch_meta = metadatas[start:end]

        try:
            collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta,
            )
            ingested += len(batch_ids)
            logger.debug(
                "Batch ingested: %d-%d / %d (philosopher=%d, work=%d)",
                start,
                end,
                len(chunks),
                philosopher_id,
                work_id,
            )
        except Exception as exc:
            raise RuntimeError(
                f"ChromaDB batch yazma hatası "
                f"(philosopher={philosopher_id}, work={work_id}, "
                f"batch={start}-{end}): {exc}"
            ) from exc

    logger.info(
        "Ingestion tamamlandı: philosopher=%d, work=%d, %d chunk kaydedildi",
        philosopher_id,
        work_id,
        ingested,
    )
    return ingested


def query_chunks(
    philosopher_id: int,
    query_text: str,
    n_results: int = 5,
    work_id: Optional[int] = None,
) -> List[dict]:
    """
    Semantik arama yapar. Artık List[str] değil List[dict] döndürür.
    Her sonuç: {"text": str, "work_title": str, "chunk_index": int}
    """
    if not query_text or not query_text.strip():
        return []

    try:
        collection = get_or_create_collection(philosopher_id)
        if collection.count() == 0:
            return []

        where_filter: Optional[Dict[str, Any]] = None
        if work_id is not None:
            where_filter = {"work_id": work_id}

        query_kwargs: Dict[str, Any] = {
            "query_texts": [query_text.strip()],
            "n_results":   min(n_results, collection.count()),
            "include":     ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        results = collection.query(**query_kwargs)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # Eser başlıklarını çek
        work_titles = _get_work_titles(
            [m.get("work_id") for m in metadatas]
        )

        enriched = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            work_id_val = meta.get("work_id")
            enriched.append({
                "text":        doc,
                "work_title":  work_titles.get(work_id_val, "Bilinmeyen Eser"),
                "chunk_index": meta.get("chunk_index", 0),
                "distance":    round(dist, 4),
            })

        logger.debug(
            "query_chunks: philosopher=%d, '%s...' → %d sonuç",
            philosopher_id, query_text[:60], len(enriched),
        )
        return enriched

    except Exception as exc:
        logger.error(
            "query_chunks başarısız (philosopher=%d): %s",
            philosopher_id, exc, exc_info=True,
        )
        return []


def _get_work_titles(work_ids: List[Optional[int]]) -> Dict[int, str]:
    """work_id listesinden eser başlıklarını toplu çeker."""
    unique_ids = [wid for wid in set(work_ids) if wid is not None]
    if not unique_ids:
        return {}
    try:
        from apps.philosophers.models import PhilosophicalWork
        works = PhilosophicalWork.objects.filter(
            pk__in=unique_ids
        ).values("id", "title")
        return {w["id"]: w["title"] for w in works}
    except Exception:
        return {}


def delete_philosopher_collection(philosopher_id: int) -> bool:
    """
    Filozofa ait tüm ChromaDB collection'ını siler.
    Admin panelinden 'eserler sıfırla' işlemi için kullanılır.

    Args:
        philosopher_id: Silinecek philosopher'ın pk'si.

    Returns:
        True — başarılı; False — collection bulunamadı.
    """
    client = _get_client()
    name = _collection_name(philosopher_id)
    try:
        client.delete_collection(name=name)
        logger.info(
            "ChromaDB collection silindi: %s (philosopher=%d)",
            name,
            philosopher_id,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Collection silinemedi: %s — %s", name, exc
        )
        return False


def delete_work_chunks(philosopher_id: int, work_id: int) -> int:
    """
    Belirli bir esere ait chunk'ları collection'dan siler.
    Eser yeniden işlendiğinde eski chunk'ları temizler.

    Args:
        philosopher_id: Philosopher pk.
        work_id:        PhilosophicalWork pk.

    Returns:
        Silinen chunk sayısı (tam sayı bilinmiyorsa 0).
    """
    try:
        collection = get_or_create_collection(philosopher_id)
        if collection.count() == 0:
            return 0

        collection.delete(where={"work_id": work_id})
        logger.info(
            "Eser chunk'ları silindi: philosopher=%d, work=%d",
            philosopher_id,
            work_id,
        )
        return 1  # ChromaDB silinen sayıyı döndürmez; 1 = başarılı
    except Exception as exc:
        logger.error(
            "delete_work_chunks başarısız (philosopher=%d, work=%d): %s",
            philosopher_id,
            work_id,
            exc,
            exc_info=True,
        )
        return 0


def get_collection_stats(philosopher_id: int) -> Dict[str, Any]:
    """
    Collection istatistiklerini döndürür (admin/debug için).

    Returns:
        {"collection_name": str, "chunk_count": int, "exists": bool}
    """
    name = _collection_name(philosopher_id)
    try:
        collection = get_or_create_collection(philosopher_id)
        return {
            "collection_name": name,
            "chunk_count": collection.count(),
            "exists": True,
        }
    except Exception:
        return {
            "collection_name": name,
            "chunk_count": 0,
            "exists": False,
        }

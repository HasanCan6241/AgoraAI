# PATH: tests/test_rag.py
"""
Agora AI — RAG Pipeline Testleri
Doküman Bölüm 6/AŞAMA 7: pdf_extractor, chroma_store ve
ingestion_pipeline birim testleri.
ChromaDB ve Gemini API çağrıları mock ile izole edilir.
"""

import pytest
from unittest.mock import MagicMock, patch

from apps.rag.services.pdf_extractor import chunk_text, _apply_overlap, _split_large_paragraph


# ── PDF Extractor Testleri ────────────────────────────────────────────────────

@pytest.mark.unit
class TestChunkText:
    """chunk_text() fonksiyonu birim testleri — IO gerektirmez."""

    def test_empty_text_returns_empty_list(self):
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert chunk_text("   \n\n   ") == []

    def test_short_text_returns_single_chunk(self):
        text = "Bu kısa bir metindir."
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert "kısa" in chunks[0]

    def test_long_text_is_split_into_multiple_chunks(self):
        # 3000 karakterlik metin
        long_text = ("Sokrates dedi ki. " * 200).strip()
        chunks = chunk_text(long_text, chunk_size=800, chunk_overlap=100)
        assert len(chunks) > 1

    def test_chunk_size_respected(self):
        long_text = "A" * 5000
        chunks = chunk_text(long_text, chunk_size=800, chunk_overlap=0)
        for chunk in chunks:
            assert len(chunk) <= 900  # overlap payı ile tolerans

    def test_min_chunk_length_filters_short_chunks(self):
        text = "Kısa.\n\nBu uzun bir paragraftır ve yeterli uzunluğa sahiptir. " * 10
        chunks = chunk_text(text, min_chunk_length=50)
        for chunk in chunks:
            assert len(chunk) >= 50

    def test_overlap_creates_context_bridge(self):
        chunks = ["Bu birinci chunk metnidir.", "Bu ikinci chunk metnidir."]
        overlapped = _apply_overlap(chunks, overlap=10)
        assert len(overlapped) == 2
        # İkinci chunk'ın başında birinci chunk'ın sonu olmalı
        assert overlapped[1].startswith(chunks[0][-10:])

    def test_overlap_zero_returns_original(self):
        chunks = ["Birinci.", "İkinci."]
        result = _apply_overlap(chunks, overlap=0)
        assert result == chunks

    def test_paragraph_splitting_on_double_newline(self):
        text = "Paragraf bir.\n\nParagraf iki.\n\nParagraf üç."
        chunks = chunk_text(text, chunk_size=50)
        assert len(chunks) >= 1

    def test_split_large_paragraph_returns_list(self):
        big_paragraph = "Bu bir cümle. " * 100
        result = _split_large_paragraph(big_paragraph, chunk_size=200, chunk_overlap=50)
        assert isinstance(result, list)
        assert len(result) > 1


@pytest.mark.unit
class TestExtractText:
    """extract_text() fonksiyonu — dosya IO mock edilir."""

    def test_unsupported_extension_raises(self, tmp_path):
        fake_file = tmp_path / "test.docx"
        fake_file.write_text("test")
        from apps.rag.services.pdf_extractor import extract_text
        with pytest.raises(ValueError, match="Desteklenmeyen dosya türü"):
            extract_text(str(fake_file))

    def test_txt_extraction_utf8(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Sokrates Atina'nın büyük filozofudur.", encoding="utf-8")
        from apps.rag.services.pdf_extractor import extract_text
        result = extract_text(str(txt_file))
        assert "Sokrates" in result

    def test_nonexistent_file_raises(self):
        from apps.rag.services.pdf_extractor import extract_text
        with pytest.raises(ValueError, match="Dosya bulunamadı"):
            extract_text("/tmp/nonexistent_agora_test.txt")


# ── ChromaDB Store Testleri ───────────────────────────────────────────────────

@pytest.mark.unit
class TestChromaStore:
    """ChromaDB fonksiyonları — client mock edilir."""

    @patch("apps.rag.services.chroma_store._get_client")
    def test_ingest_chunks_calls_collection_add(self, mock_get_client):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client

        from apps.rag.services.chroma_store import ingest_chunks
        count = ingest_chunks(
            philosopher_id=1,
            work_id=1,
            chunks=["chunk1", "chunk2", "chunk3"],
        )
        assert count == 3
        assert mock_collection.add.called

    @patch("apps.rag.services.chroma_store._get_client")
    def test_ingest_empty_chunks_returns_zero(self, mock_get_client):
        from apps.rag.services.chroma_store import ingest_chunks
        result = ingest_chunks(philosopher_id=1, work_id=1, chunks=[])
        assert result == 0
        mock_get_client.assert_not_called()

    @patch("apps.rag.services.chroma_store._get_client")
    def test_query_chunks_returns_list(self, mock_get_client):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 5
        mock_collection.query.return_value = {
            "documents": [["chunk A", "chunk B", "chunk C"]]
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client

        from apps.rag.services.chroma_store import query_chunks
        results = query_chunks(philosopher_id=1, query_text="Eudaimonia nedir?")
        assert isinstance(results, list)
        assert "chunk A" in results

    @patch("apps.rag.services.chroma_store._get_client")
    def test_query_chunks_empty_collection_returns_empty(self, mock_get_client):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client

        from apps.rag.services.chroma_store import query_chunks
        results = query_chunks(philosopher_id=1, query_text="test")
        assert results == []

    @patch("apps.rag.services.chroma_store._get_client")
    def test_query_chunks_empty_query_returns_empty(self, mock_get_client):
        from apps.rag.services.chroma_store import query_chunks
        results = query_chunks(philosopher_id=1, query_text="")
        assert results == []
        mock_get_client.assert_not_called()

    @patch("apps.rag.services.chroma_store._get_client")
    def test_query_chunks_exception_returns_empty(self, mock_get_client):
        mock_get_client.side_effect = RuntimeError("ChromaDB bağlantı hatası")
        from apps.rag.services.chroma_store import query_chunks
        results = query_chunks(philosopher_id=1, query_text="test")
        assert results == []


# ── Ingestion Pipeline Testleri ───────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestIngestionPipeline:
    """run_ingestion() fonksiyonu — tüm dış bağımlılıklar mock edilir."""

    @patch("apps.rag.services.ingestion_pipeline.ingest_chunks")
    @patch("apps.rag.services.ingestion_pipeline.delete_work_chunks")
    @patch("apps.rag.services.ingestion_pipeline.chunk_text")
    @patch("apps.rag.services.ingestion_pipeline.extract_text")
    def test_successful_ingestion(
        self,
        mock_extract,
        mock_chunk,
        mock_delete,
        mock_ingest,
        philosophical_work,
    ):
        """Başarılı ingestion sonucu status 'completed' olmalı."""
        # Dosya yolunu ayarla
        philosophical_work.original_file = MagicMock()
        philosophical_work.original_file.path = "/tmp/test.txt"
        philosophical_work.save = MagicMock()

        mock_extract.return_value = "Test felsefi metin içeriği."
        mock_chunk.return_value = ["chunk1", "chunk2", "chunk3"]
        mock_delete.return_value = 0
        mock_ingest.return_value = 3

        from apps.rag.services.ingestion_pipeline import run_ingestion
        success, msg = run_ingestion(work_id=philosophical_work.pk)

        assert success is True
        assert "3 chunk" in msg

    def test_nonexistent_work_returns_failure(self):
        """Varolmayan work_id için False dönmeli."""
        from apps.rag.services.ingestion_pipeline import run_ingestion
        success, msg = run_ingestion(work_id=999999)
        assert success is False
        assert "bulunamadı" in msg.lower()

    @patch("apps.rag.services.ingestion_pipeline.extract_text")
    def test_missing_file_returns_failure(self, mock_extract, philosopher):
        """Dosyası olmayan eser için False dönmeli."""
        from apps.philosophers.models import PhilosophicalWork
        work = PhilosophicalWork.objects.create(
            philosopher=philosopher,
            title="Dosyasız Eser",
            ingestion_status=PhilosophicalWork.STATUS_PENDING,
        )
        from apps.rag.services.ingestion_pipeline import run_ingestion
        success, msg = run_ingestion(work_id=work.pk)
        assert success is False
        mock_extract.assert_not_called()

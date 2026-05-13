# PATH: apps/rag/services/pdf_extractor.py
"""
Agora AI — PDF / TXT Metin Çıkarıcı
Doküman Bölüm 4.2 (RAG Pipeline) ve Bölüm 7.2 (Ingestion akışı) referans alınmıştır.

Akış (Doküman Bölüm 4.2):
    Dosya (PDF/TXT) → extract_text() → ham metin (str)
    Ham metin → chunk_text() → chunk listesi
    Chunk listesi → ChromaDB'ye embed_and_store() (chroma_store.py)

Kullanılan kütüphane: PyMuPDF (fitz) — requirements.txt: PyMuPDF==1.24.5
"""

from __future__ import annotations

import logging
import os
import re
from typing import List

import fitz

logger = logging.getLogger("agora.rag.extractor")

# ── Sabitler (Doküman Bölüm 7.2) ─────────────────────────────────────────────
CHUNK_SIZE = 1800       # karakter cinsinden hedef chunk büyüklüğü
CHUNK_OVERLAP = 200     # ardışık chunk'lar arasındaki örtüşme (bağlamı korur)
MIN_CHUNK_LENGTH = 100  # bu kadar karakterden kısa chunk'lar atılır

# Derleme maliyetini önceden öde — her çağrıda yeniden derleme yapma
_RE_HYPHEN_BREAK = re.compile(r"-\n(\w)")          # tire-satırsonu birleştirme
_RE_LONE_NUMBER = re.compile(r"^\s*\d+\s*$", re.MULTILINE)  # sayfa numaraları
_RE_EXCESS_NEWLINES = re.compile(r"\n{3,}")         # üç+ boş satır
_RE_EXCESS_SPACES = re.compile(r"[ \t]{2,}")        # fazla yatay boşluk
# Yeni
_ABBREVS = r"(?:Prof|Dr|Mr|Mrs|Ms|Sr|Jr|St|vb|vs|bkz|a\.g\.e|mad|No|Vol|Ed)"
# Her kısaltma kendi sabit uzunluklu lookbehind bloğuna alındı (Python 're' uyumlu)
_RE_SENTENCE_END = re.compile(
    r"(?<!\bProf)(?<!\bDr)(?<!\bMr)(?<!\bMrs)(?<!\bMs)(?<!\bSr)(?<!\bJr)"
    r"(?<!\bSt)(?<!\bvb)(?<!\bvs)(?<!\bbkz)(?<!a\.g\.e)(?<!\bmad)(?<!\bNo)(?<!\bVol)(?<!\bEd)"
    r"(?<=[.!?…])\s+(?=[A-ZÇĞİÖŞÜ\"'])"
)

# Sabitleri güncelliyoruz (Daha güvenli varsayılanlar)
_HEADER_FOOTER_MARGIN = 0.05   # %8'den %5'e düşürüldü (gerçek metni kesmemek için)
_COLUMN_GAP_RATIO     = 0.50   # 0.45'ten 0.50'ye çekildi (tam orta nokta)

def _extract_page_text(
    page,
    margin_ratio: float = _HEADER_FOOTER_MARGIN,
    split_ratio: float = _COLUMN_GAP_RATIO
) -> str:
    """
    Tek sayfadan koordinat-farkındalıklı metin çıkarır.
    İleride kitap bazlı (per-document) özel ayarlar gelirse diye
    margin_ratio ve split_ratio parametrik yapılmıştır.
    """
    page_rect = page.rect                        # (x0, y0, x1, y1)
    page_h    = page_rect.height
    page_w    = page_rect.width

    header_limit = page_rect.y0 + page_h * margin_ratio
    footer_limit = page_rect.y1 - page_h * margin_ratio
    col_split    = page_rect.x0 + page_w * split_ratio

    # Performans notu: 'dict' metodu yavaştır ancak RAG ingestion pipeline'ı
    # arka planda çalıştığı için semantik bütünlük adına bu maliyet kabul edilir.
    data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    left_lines:  List[tuple] = []   # (y0, text)
    right_lines: List[tuple] = []

    for block in data.get("blocks", []):
        if block.get("type") != 0:          # Sadece metin bloklarını al
            continue

        b_y0 = block["bbox"][1]
        b_y1 = block["bbox"][3]
        b_x0 = block["bbox"][0]

        # ── Header / Footer filtresi ────────────────────────────────────────
        if b_y1 <= header_limit or b_y0 >= footer_limit:
            continue

        # ── Satırları topla ─────────────────────────────────────────────────
        for line in block.get("lines", []):
            line_text = " ".join(
                span["text"] for span in line.get("spans", [])
            ).strip()
            if not line_text:
                continue

            line_y = line["bbox"][1]

            # Başlangıç koordinatı sayfanın sol yarısındaysa sol sütuna (veya tek sütuna),
            # sağ yarısındaysa sağ sütuna ekle.
            if b_x0 < col_split:
                left_lines.append((line_y, line_text))
            else:
                right_lines.append((line_y, line_text))

    # ── Sütunları y-koordinatına göre sırala ve birleştir ───────────────────
    left_lines.sort(key=lambda t: t[0])
    right_lines.sort(key=lambda t: t[0])

    all_lines = [text for _, text in left_lines + right_lines]
    return "\n".join(all_lines)


# ── PDF Çıkarımı ──────────────────────────────────────────────────────────────


def extract_text_from_pdf(file_path: str) -> str:
    """
    PyMuPDF (fitz) ile PDF dosyasından düz metin çıkarır.

    Args:
        file_path: PDF dosyasının tam yolu.

    Returns:
        Temizlenmiş, birleştirilmiş sayfa metni.

    Raises:
        ValueError: Dosya bulunamazsa veya hiç metin yoksa.
        RuntimeError: PyMuPDF import veya açma hatası.
    """
    try:
        import fitz  # PyMuPDF — isteğe bağlı bağımlılık, burada import etmek kasıtlı
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF kurulu değil. `pip install PyMuPDF` komutunu çalıştırın."
        ) from exc

    if not os.path.exists(file_path):
        raise ValueError(f"Dosya bulunamadı: {file_path}")

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise RuntimeError(f"PDF açılamadı: {file_path} — {exc}") from exc

    pages_text: List[str] = []
    for page_num in range(len(doc)):
        try:
            page = doc.load_page(page_num)
            text = _extract_page_text(page)  # ← eski: page.get_text("text")
            if text.strip():
                pages_text.append(text)
        except Exception as page_exc:
            logger.warning(
                "Sayfa %d okunamadı (%s): %s",
                page_num + 1,
                os.path.basename(file_path),
                page_exc,
            )

    doc.close()

    if not pages_text:
        raise ValueError(
            f"PDF'den metin çıkarılamadı: {file_path}. "
            "Dosya taranmış görsel içeriyor olabilir."
        )

    full_text = _clean_pdf_text("\n\n".join(pages_text))

    logger.info(
        "PDF çıkartıldı: %s — %d sayfa, %d karakter",
        os.path.basename(file_path),
        len(pages_text),
        len(full_text),
    )
    return full_text



def _clean_pdf_text(text: str) -> str:
    """
    PDF'den gelen ham metni normalize eder.
    Orijinal metinden ayrı tutulması test edilebilirliği artırır.
    """
    text = _RE_HYPHEN_BREAK.sub(r"\1", text)      # "keli-\nme" → "kelime"
    text = _RE_LONE_NUMBER.sub("", text)           # sayfa numaralarını sil
    text = _RE_EXCESS_NEWLINES.sub("\n\n", text)   # boş satırları normalize et
    text = _RE_EXCESS_SPACES.sub(" ", text)        # yatay boşlukları temizle
    return text.strip()


# ── TXT Çıkarımı ──────────────────────────────────────────────────────────────

def extract_text_from_txt(file_path: str) -> str:
    """
    Düz TXT dosyasından metin okur; encoding'i otomatik saptar.

    Args:
        file_path: TXT dosyasının tam yolu.

    Returns:
        Dosya içeriği.

    Raises:
        ValueError: Dosya bulunamazsa veya encoding okunamazsa.
    """
    if not os.path.exists(file_path):
        raise ValueError(f"Dosya bulunamadı: {file_path}")

    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(file_path, "r", encoding=encoding) as fh:
                content = fh.read().strip()
            if content:
                logger.info(
                    "TXT çıkartıldı: %s — %d karakter (%s)",
                    os.path.basename(file_path),
                    len(content),
                    encoding,
                )
                return content
        except UnicodeDecodeError:
            continue

    raise ValueError(
        f"TXT dosyası okunamadı (desteklenmeyen encoding): {file_path}"
    )


# ── Yönlendirici ──────────────────────────────────────────────────────────────

def extract_text(file_path: str) -> str:
    """
    Dosya uzantısına göre uygun çıkarıcıyı seçer.
    Doküman Bölüm 7.4: Yalnızca .pdf ve .txt desteklenir.

    Raises:
        ValueError: Desteklenmeyen dosya türü.
    """
    ext = os.path.splitext(file_path)[1].lower()
    extractors = {
        ".pdf": extract_text_from_pdf,
        ".txt": extract_text_from_txt,
    }
    if ext not in extractors:
        raise ValueError(
            f"Desteklenmeyen dosya türü: '{ext}'. "
            "Yalnızca .pdf ve .txt kabul edilmektedir."
        )
    return extractors[ext](file_path)


# ── Chunklama ─────────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    min_chunk_length: int = MIN_CHUNK_LENGTH,
) -> List[str]:
    """
    Ham metni anlam sınırlarını koruyarak örtüşen chunk'lara böler.

    Strateji:
        1. Çift satır sonu (\\n\\n) ile paragraflara böl.
        2. Paragraf chunk_size'dan büyükse cümle sonu ile alt böl.
        3. Yine büyükse karakter bazlı kes; overlap ile bağlam köprüsü kur.
        4. Ardışık chunk'lara sliding-window overlap uygula.
        5. MIN_CHUNK_LENGTH altındaki chunk'ları at.

    Args:
        text:             Bölünecek ham metin.
        chunk_size:       Hedef chunk karakter uzunluğu (varsayılan: 1800).
        chunk_overlap:    Sliding-window örtüşme miktarı (varsayılan: 200).
        min_chunk_length: Bu uzunluktan kısa chunk'lar sonuçtan çıkarılır.

    Returns:
        Chunk string listesi.
    """
    if not text or not text.strip():
        return []

    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current_chunk = ""

    for paragraph in raw_paragraphs:
        candidate_len = len(current_chunk) + len(paragraph) + 2  # +2: "\n\n"

        if candidate_len <= chunk_size:
            current_chunk = (
                current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            )
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            if len(paragraph) > chunk_size:
                chunks.extend(
                    _split_large_paragraph(paragraph, chunk_size, chunk_overlap)
                )
                current_chunk = ""
            else:
                current_chunk = paragraph

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Sliding-window overlap — orijinal chunk'ları bozmaz
    overlapped = _apply_sliding_overlap(chunks, chunk_overlap)

    final = [c for c in overlapped if len(c) >= min_chunk_length]

    logger.debug(
        "Chunklama: %d paragraf → %d chunk (size=%d, overlap=%d)",
        len(raw_paragraphs),
        len(final),
        chunk_size,
        chunk_overlap,
    )
    return final


def _split_large_paragraph(
    text: str, chunk_size: int, chunk_overlap: int
) -> List[str]:
    """
    Büyük bir paragrafı önce cümle sınırlarından, gerekirse
    karakter bazlı sliding-window ile böler.
    """
    sentences = _RE_SENTENCE_END.split(text)
    sub_chunks: List[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = (current + " " + sentence).lstrip() if current else sentence
        else:
            if current:
                sub_chunks.append(current.strip())
            if len(sentence) > chunk_size:
                # Tek cümle bile chunk_size'ı aşıyorsa sliding-window uygula
                start = 0
                while start < len(sentence):
                    sub_chunks.append(sentence[start : start + chunk_size].strip())
                    start += chunk_size - chunk_overlap
                current = ""
            else:
                current = sentence

    if current.strip():
        sub_chunks.append(current.strip())

    return sub_chunks


def _apply_sliding_overlap(chunks: List[str], overlap: int) -> List[str]:
    """
    Sliding-window overlap: her chunk'ın başına bir önceki chunk'ın
    son `overlap` karakterini ekler.

    Orijinal `[...]` ayracı yerine doğal geçiş sağlar —
    bu sayede embedding modeli bağlamı daha iyi yakalar.
    """
    if len(chunks) <= 1 or overlap <= 0:
        return chunks

    result: List[str] = [chunks[0]]
    for i in range(1, len(chunks)):
        tail = chunks[i - 1][-overlap:]
        # Tail'i bir önceki cümle sınırından başlat (varsa)
        boundary = tail.find(" ")
        if 0 < boundary < len(tail) // 2:
            tail = tail[boundary:].lstrip()
        result.append(tail + " " + chunks[i])

    return result
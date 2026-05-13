# PATH: apps/conversations/services/deepseek_client.py
"""
Agora AI — DeepSeek AI İstemcisi
OpenAI SDK üzerinden DeepSeek API kullanılır.
Model: deepseek-chat (DeepSeek-V3)
"""

import logging
from typing import Generator, List

from django.conf import settings

logger = logging.getLogger("agora.conversations.gemini")

# Model adı
DEEPSEEK_MODEL = "deepseek-chat"

# Singleton client
_deepseek_client = None


def _get_client(user=None):
    """
    DeepSeek client'ı döndürür.
    Her kullanıcı yalnızca kendi API key'ini kullanabilir.
    .env'deki varsayılan key artık kullanılmıyor.
    """
    from openai import OpenAI

    api_key = None

    if user and hasattr(user, "deepseek_api_key") and user.deepseek_api_key:
        api_key = user.deepseek_api_key.strip()

    if not api_key:
        raise ValueError(
            "API anahtarı bulunamadı. Lütfen profil ayarlarınızdan "
            "DeepSeek API anahtarınızı ekleyin."
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    logger.debug("DeepSeek client oluşturuldu: model=%s", DEEPSEEK_MODEL)
    return client


def generate_response_stream(
    system_prompt: str,
    message_history: List[dict],
    user_message: str,
    user=None,
) -> Generator[str, None, None]:
    """
    DeepSeek API'ye streaming isteği gönderir, token token yield eder.
    SSE ile tarayıcıya iletilir.

    Args:
        system_prompt:   Filozof persona + RAG bağlamı
        message_history: Geçmiş mesajlar (Gemini formatından dönüştürülür)
        user_message:    Kullanıcının güncel mesajı

    Yields:
        Metin token'ları (str)
    """
    try:
        client = _get_client(user=user)   # ← user geç

        # Mesaj geçmişini OpenAI formatına dönüştür
        # Gemini: {"role": "user/model", "parts": [{"text": "..."}]}
        # OpenAI: {"role": "user/assistant", "content": "..."}
        messages = [{"role": "system", "content": system_prompt}]

        for msg in message_history:
            role = msg.get("role", "user")
            # Gemini "model" → OpenAI "assistant"
            if role == "model":
                role = "assistant"
            # parts listesinden metni çıkar
            parts = msg.get("parts", [])
            if parts and isinstance(parts[0], dict):
                content = parts[0].get("text", "")
            else:
                content = str(parts[0]) if parts else ""

            if content:
                messages.append({"role": role, "content": content})

        # Kullanıcı mesajını ekle
        messages.append({"role": "user", "content": user_message})

        # Streaming isteği
        stream = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            stream=True,
            max_tokens=2048,
            temperature=0.7,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    except Exception as exc:
        error_type = type(exc).__name__
        logger.error(
            "DeepSeek streaming hatası: %s — %s",
            error_type, exc, exc_info=True,
        )
        yield _build_error_message(exc)


def generate_response_sync(
    system_prompt: str,
    message_history: List[dict],
    user_message: str,
    user=None
) -> str:
    """
    DeepSeek API'ye senkron istek gönderir.
    Sempozyum modu ve bağlam özetleme için kullanılır.

    Returns:
        Tam yanıt metni (str)
    """
    try:
        client = _get_client(user=user)  # ← user geç

        messages = [{"role": "system", "content": system_prompt}]

        for msg in message_history:
            role = msg.get("role", "user")
            if role == "model":
                role = "assistant"
            parts = msg.get("parts", [])
            if parts and isinstance(parts[0], dict):
                content = parts[0].get("text", "")
            else:
                content = str(parts[0]) if parts else ""
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            stream=False,
            max_tokens=2048,
            temperature=0.7,
        )

        return response.choices[0].message.content or ""

    except Exception as exc:
        logger.error(
            "DeepSeek senkron istek hatası: %s — %s",
            type(exc).__name__, exc, exc_info=True,
        )
        return _build_error_message(exc)


def summarize_conversation(messages_text: str, user=None) -> str:   # ← ekle
    """
    Uzun sohbetleri özetler.
    Doküman Bölüm 5.2: Bağlam penceresi yönetimi.

    Args:
        messages_text: Özetlenecek mesaj metni

    Returns:
        Kısa özet metni
    """
    summarize_prompt = (
        "Aşağıdaki felsefi sohbeti 3-5 cümle ile özetle. "
        "Ana tartışma konularını, varılan sonuçları ve önemli argümanları "
        "belirt. Özeti Türkçe yaz.\n\n"
        f"Sohbet:\n{messages_text}"
    )

    try:
        client = _get_client(user=user)   # ← user geç
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Sen felsefi sohbetleri özetleyen bir asistansın."},
                {"role": "user", "content": summarize_prompt},
            ],
            stream=False,
            max_tokens=500,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.error("Özetleme hatası: %s", exc, exc_info=True)
        return ""


def _build_error_message(exc: Exception) -> str:
    """Kullanıcıya gösterilecek hata mesajını üretir."""
    error_str  = str(exc).upper()
    error_type = type(exc).__name__

    if "API_KEY" in error_str or "AUTHENTICATION" in error_str or "401" in error_str:
        return (
            "\n\n⚠️ *Bağlantı hatası:* DeepSeek API anahtarı geçersiz veya eksik. "
            "Lütfen .env dosyasındaki DEEPSEEK_API_KEY değerini kontrol edin."
        )
    elif "QUOTA" in error_str or "429" in error_str or "RATE" in error_str:
        return (
            "\n\n⚠️ *Geçici yoğunluk:* API istek limiti aşıldı. "
            "Lütfen birkaç saniye bekleyip tekrar deneyin."
        )
    elif "TIMEOUT" in error_str or "TIMED OUT" in error_str:
        return (
            "\n\n⚠️ *Zaman aşımı:* Sunucu yanıt vermedi. "
            "Lütfen tekrar deneyin."
        )
    elif "CONNECTION" in error_str:
        return (
            "\n\n⚠️ *Bağlantı hatası:* DeepSeek sunucusuna ulaşılamıyor. "
            "İnternet bağlantınızı kontrol edin."
        )
    else:
        return (
            f"\n\n⚠️ *Teknik hata ({error_type}):* Yanıt üretilirken bir sorun oluştu. "
            "Lütfen tekrar deneyin."
        )
# PATH: apps/conversations/views.py
"""
Agora AI — Sohbet Görünümleri (Views)
Doküman Bölüm 5.2 (Sohbet Akışı) ve 5.3 (SSE Streaming) referans alınmıştır.

Akış (Doküman Bölüm 5.2):
    POST /conversations/new/<slug>/ → ConversationSession oluştur → redirect
    GET  /conversations/<id>/       → Sohbet sayfası (chat arayüzü)
    POST /conversations/<id>/send/  → Mesaj kaydet → SSE stream tetikle
    GET  /conversations/<id>/stream/ → StreamingHttpResponse (SSE)
    GET  /conversations/            → Kullanıcının tüm sohbetleri

Doküman Bölüm 5.3 — SSE:
    Content-Type: text/event-stream
    data: <token>\n\n  formatında token token gönderilir
    Nginx: proxy_buffering off (AŞAMA 1'de konfigüre edildi)
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.philosophers.models import Philosopher
from apps.rag.services.chroma_store import query_chunks

from .models import ConversationSession, Message
from .services.gemini_client import (
    generate_response_stream,
    summarize_conversation,
)
from .services.prompt_builder import PromptBuilder
from django.contrib import messages

logger = logging.getLogger("agora.conversations.views")

# Kaç mesajdan sonra özet alınsın (Doküman Bölüm 5.2)
SUMMARIZE_AFTER_MESSAGES = 20
# Özetten sonra kaç mesaj sliding window'da tutulsun
SLIDING_WINDOW_SIZE = 10


# ── 1. Sohbet Listesi ─────────────────────────────────────────────────────────
@login_required
@require_http_methods(["GET"])
def conversation_list(request):
    """
    Kullanıcının tüm aktif sohbet oturumlarını listeler.
    GET /conversations/
    """
    philosopher_filter = request.GET.get("philosopher", "").strip()

    sessions = ConversationSession.objects.filter(
        user=request.user,
        is_active=True,
    ).select_related("philosopher").prefetch_related("messages")

    if philosopher_filter:
        sessions = sessions.filter(philosopher__slug=philosopher_filter)

    # Her oturum için son mesajı ve mesaj sayısını ekle
    sessions_data = []
    for session in sessions:
        last_msg = session.last_message
        sessions_data.append(
            {
                "session": session,
                "last_message": last_msg,
                "message_count": session.get_message_count(),
            }
        )

    context = {
        "sessions_data": sessions_data,
        "philosopher_filter": philosopher_filter,
        "total_count": len(sessions_data),
    }
    return render(request, "conversations/conversation_list.html", context)


# ── 2. Yeni Sohbet Başlat ─────────────────────────────────────────────────────
@login_required
@require_http_methods(["GET", "POST"])
def new_conversation(request, philosopher_slug: str):
    """
    Verilen filozofla yeni bir ConversationSession oluşturur.
    GET  → Confirm sayfası (opsiyonel, direkt POST'a da gönderilebilir)
    POST → Session oluştur → redirect /conversations/<id>/
    Doküman Bölüm 5.2: Oturum oluşturulurken zeitgeist_mode kullanıcı
    profilinden kopyalanır.
    """
    philosopher = get_object_or_404(Philosopher, slug=philosopher_slug, is_active=True)

    if request.method == "POST" or request.method == "GET":
        # Zeitgeist modunu kullanıcının profilinden al
        zeitgeist_mode = request.user.zeitgeist_mode

        # Filozofun varsayılan modunu veritabanından al
        from apps.philosophers.models import PhilosopherMode
        try:
            default_phil_mode = PhilosopherMode.objects.get(
                philosopher=philosopher,
                is_default=True,
                is_active=True,
            )
            default_mode = default_phil_mode.mode_key
        except PhilosopherMode.DoesNotExist:
            default_mode = "normal"

        # API key kontrolü
        if not request.user.deepseek_api_key:
            messages.error(
                request,
                "Sohbet başlatmak için önce profil ayarlarınızdan "
                "DeepSeek API anahtarınızı ekleyin. "
                "Anahtarı platform.deepseek.com adresinden alabilirsiniz."
            )
            return redirect("accounts:profile")

        # URL parametresiyle override: ?mode=normal
        requested_mode = request.GET.get("mode", default_mode)

        # İstenen mod bu filozofa ait mi kontrol et
        valid_modes = list(
            PhilosopherMode.objects.filter(
                philosopher=philosopher, is_active=True
            ).values_list("mode_key", flat=True)
        ) + ["normal"]

        mode = requested_mode if requested_mode in valid_modes else default_mode

        # URL parametresiyle override edilebilir: ?mode=normal
        mode = request.GET.get("mode", default_mode)
        if mode not in ("normal", "socratic"):
            mode = default_mode

        session = ConversationSession.objects.create(
            user=request.user,
            philosopher=philosopher,
            zeitgeist_mode=request.user.zeitgeist_mode,
            mode=mode,
            title=f"{philosopher.name} ile Sohbet — {timezone.now():%d.%m.%Y}",
        )

        logger.info(
            "Yeni sohbet oturumu: user=%s, philosopher=%s, session=%d, zeitgeist=%s",
            request.user.username,
            philosopher.name,
            session.pk,
            zeitgeist_mode,
        )

        return redirect("conversations:chat", session_id=session.pk)

    return render(
        request,
        "conversations/new_conversation.html",
        {"philosopher": philosopher},
    )


# ── views.py ─────────────────────────────────────────────────────────
@login_required
@require_http_methods(["GET"])
def chat_view(request, session_id: int):
    session = get_object_or_404(
        ConversationSession,
        pk=session_id,
        user=request.user,
        is_active=True,
    )
    philosopher = session.philosopher

    # DEĞİŞİKLİK: messages değişkeninin adını chat_messages yaptık
    chat_messages = session.messages.order_by("created_at")

    context = {
        "session": session,
        "philosopher": philosopher,
        "chat_messages": chat_messages,  # <-- BURASI GÜNCELLENDİ
        "zeitgeist_mode": session.zeitgeist_mode,
        "zeitgeist_display": session.get_zeitgeist_mode_display(),
    }
    return render(request, "conversations/chat.html", context)


# ── 4. Mesaj Gönder (AJAX) ────────────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def send_message(request, session_id: int):
    """
    Kullanıcı mesajını kaydeder ve stream URL'ini döndürür.
    POST /conversations/<session_id>/send/
    Doküman Bölüm 5.2: Sohbet Akışı adım 1-3.

    İstek gövdesi (JSON): {"message": "Eudaimonia nedir?"}
    Yanıt (JSON): {"message_id": int, "stream_url": str}
    """
    session = get_object_or_404(
        ConversationSession,
        pk=session_id,
        user=request.user,
        is_active=True,
    )

    # İstek gövdesini ayrıştır
    try:
        body = json.loads(request.body)
        user_text = body.get("message", "").strip()
    except (json.JSONDecodeError, AttributeError):
        user_text = request.POST.get("message", "").strip()

    if not user_text:
        return JsonResponse({"error": "Mesaj boş olamaz."}, status=400)

    if len(user_text) > 4000:
        return JsonResponse(
            {"error": "Mesaj 4000 karakterden uzun olamaz."}, status=400
        )

    # Kullanıcı mesajını kaydet (Doküman Bölüm 5.2, Adım 1)
    user_message = Message.objects.create(
        session=session,
        role=Message.ROLE_USER,
        content=user_text,
    )

    # Oturumun başlığını güncelle (ilk mesajdan türet)
    if session.messages.count() == 1:
        session.title = user_text[:100]
        session.save(update_fields=["title"])

    # Bağlam özetleme kontrolü (Doküman Bölüm 5.2)
    _maybe_summarize(session)

    logger.info(
        "Mesaj alındı: session=%d, user=%s, msg_id=%d, len=%d",
        session.pk,
        request.user.username,
        user_message.pk,
        len(user_text),
    )

    # Stream URL'ini döndür
    stream_url = f"/conversations/{session.pk}/stream/{user_message.pk}/"
    return JsonResponse(
        {
            "message_id": user_message.pk,
            "stream_url": stream_url,
        }
    )


# ── 5. SSE Streaming Yanıt ────────────────────────────────────────────────────
@login_required
@require_http_methods(["GET"])
def stream_response(request, session_id: int, message_id: int):
    """
    GET /conversations/<session_id>/stream/<message_id>/
    Doküman Bölüm 5.3: SSE — Content-Type: text/event-stream.

    Akış (Doküman Bölüm 5.2, Adım 4-7):
        4. Son N mesajı çek (sliding window)
        5. RAG: ChromaDB'den ilgili chunk'ları sorgula
        6. PromptBuilder ile sistem promptunu oluştur
        7. Gemini streaming yanıtını SSE ile tarayıcıya ilet
        8. Tamamlandığında Message olarak kaydet
    """
    session = get_object_or_404(
        ConversationSession,
        pk=session_id,
        user=request.user,
        is_active=True,
    )
    user_message = get_object_or_404(
        Message,
        pk=message_id,
        session=session,
        role=Message.ROLE_USER,
    )

    def event_stream():
        """
        SSE generator — her token 'data: <text>\n\n' formatında yield edilir.
        Doküman Bölüm 5.3.
        """
        philosopher = session.philosopher
        full_response = []

        try:
            # ── Adım 4: Sliding window mesaj geçmişi (Doküman Bölüm 5.2) ──
            recent_messages = session.get_recent_messages(
                count=SLIDING_WINDOW_SIZE
            )
            # Son mesaj henüz asistan yanıtı olmadan listedeyse çıkar
            history_messages = [
                m for m in recent_messages
                if m.pk != user_message.pk
            ]

            # ── Adım 5: RAG sorgusu (Doküman Bölüm 4.2) ──────────────────
            # Hibrit sorgu: son mesaj + önceki mesajlardan bağlam
            hybrid_query = user_message.content
            # Mesaj uzunluğuna göre chunk sayısını ayarla
            msg_length = len(user_message.content)
            if msg_length < 50:
                n_results = 3  # Kısa soru — az chunk
            elif msg_length < 200:
                n_results = 5  # Orta soru — normal
            else:
                n_results = 7  # Uzun/karmaşık soru — fazla chunk

            rag_chunks = query_chunks(
                philosopher_id=philosopher.pk,
                query_text=hybrid_query[:1000],
                n_results=n_results,
            )

            # Bu sohbette daha önce kullanılan chunk'ları al
            used_chunks = set()
            for msg in history_messages:
                if hasattr(msg, 'rag_chunks_used') and msg.rag_chunks_used:
                    for chunk in msg.rag_chunks_used:
                        if isinstance(chunk, dict):
                            used_chunks.add(chunk.get("text", "")[:100])
                        elif isinstance(chunk, str):
                            used_chunks.add(chunk[:100])

            # Daha önce kullanılmamış chunk'ları tercih et
            fresh_chunks = [
                c for c in rag_chunks
                if (c.get("text", "") if isinstance(c, dict) else c)[:100]
                   not in used_chunks
            ]

            # Yeterli taze chunk varsa onları kullan, yoksa hepsini kullan
            rag_chunks = fresh_chunks if len(fresh_chunks) >= 2 else rag_chunks

            # Alakasız chunk'ları filtrele (distance > 1.5 ise çok uzak)
            rag_chunks = [
                chunk for chunk in rag_chunks
                # Daha sıkı — yalnızca gerçekten alakalı chunk'lar
                if isinstance(chunk, dict) and chunk.get("distance", 0) < 1.8
                   or isinstance(chunk, str)
            ]
            logger.debug(
                "RAG sorgusu: philosopher=%s, query='%s...', chunks=%d",
                philosopher.name,
                user_message.content[:50],
                len(rag_chunks),
            )

            # ── Adım 6: Prompt oluştur (Doküman Bölüm 7.1) ───────────────
            builder = PromptBuilder(philosopher, session)
            system_prompt = builder.build_system_prompt(
                user_query=user_message.content,
                rag_chunks=rag_chunks,
            )
            message_history = builder.build_message_history(history_messages)

            # ── Adım 7: Gemini streaming (Doküman Bölüm 5.3) ─────────────
            for token in generate_response_stream(
                    system_prompt=system_prompt,
                    message_history=message_history,
                    user_message=user_message.content,
                    user=request.user,  # ← ekle
            ):
                full_response.append(token)
                # SSE formatı: "data: <token>\n\n"
                # JSON encode ederek özel karakterleri koru
                yield f"data: {json.dumps(token)}\n\n"

            # ── Adım 8: Yanıtı veritabanına kaydet ────────────────────────
            complete_text = "".join(full_response)
            if complete_text.strip():
                Message.objects.create(
                    session=session,
                    role=Message.ROLE_ASSISTANT,
                    content=complete_text,
                    rag_chunks_used=rag_chunks[:5],
                )
                # Oturumun updated_at'ini güncelle
                session.save(update_fields=["updated_at"])

            # SSE bitiş sinyali
            yield "data: [DONE]\n\n"

            logger.info(
                "Streaming tamamlandı: session=%d, tokens=%d",
                session.pk,
                len(full_response),
            )

        except Exception as exc:
            logger.error(
                "stream_response hatası: session=%d — %s",
                session.pk,
                exc,
                exc_info=True,
            )
            error_json = json.dumps(
                f"\n\n⚠️ Sunucu hatası: {type(exc).__name__}. "
                "Lütfen sayfayı yenileyin."
            )
            yield f"data: {error_json}\n\n"
            yield "data: [DONE]\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
    )
    # SSE için kritik HTTP başlıkları
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"   # Nginx proxy_buffering off
    #response["Connection"] = "keep-alive"
    return response


# ── 6. Sohbet Sil / Arşivle ──────────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def delete_conversation(request, session_id: int):
    """
    Sohbet oturumunu soft-delete (is_active=False) yapar.
    POST /conversations/<session_id>/delete/
    """
    session = get_object_or_404(
        ConversationSession,
        pk=session_id,
        user=request.user,
    )
    session.is_active = False
    session.save(update_fields=["is_active"])
    logger.info(
        "Sohbet silindi: session=%d, user=%s", session.pk, request.user.username
    )
    return JsonResponse({"success": True})


# ── Yardımcı: Bağlam Özetleme ─────────────────────────────────────────────────
def _maybe_summarize(session: ConversationSession) -> None:
    """
    Doküman Bölüm 5.2: Belirli mesaj sayısına ulaşıldığında eski mesajları
    özetleyerek ConversationSession.context_summary alanını günceller.
    """
    msg_count = session.messages.count()
    if msg_count < SUMMARIZE_AFTER_MESSAGES:
        return

    # Özetlenecek eski mesajları al (sliding window dışındakiler)
    old_messages = list(
        session.messages.order_by("created_at")[
            : msg_count - SLIDING_WINDOW_SIZE
        ]
    )
    if not old_messages:
        return

    # Metin olarak birleştir
    messages_text = "\n".join(
        f"{'Kullanıcı' if m.role == 'user' else 'Filozof'}: {m.content[:300]}"
        for m in old_messages
    )

    # Gemini ile özetle
    summary = summarize_conversation(messages_text, user=session.user)
    if summary:
        session.context_summary = summary
        session.save(update_fields=["context_summary"])
        logger.info(
            "Bağlam özeti güncellendi: session=%d, eski_mesaj=%d",
            session.pk,
            len(old_messages),
        )

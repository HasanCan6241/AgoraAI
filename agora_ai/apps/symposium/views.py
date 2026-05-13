# PATH: apps/symposium/views.py
"""
Agora AI — Dinamik Sempozyum Görünümleri (Seçenek B)
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.philosophers.models import Philosopher
from .models import SymposiumSession, SymposiumTurn

logger = logging.getLogger("agora.symposium.views")


@login_required
@require_http_methods(["GET"])
def symposium_list(request):
    # Tüm sessionları al
    sessions = (
        SymposiumSession.objects.filter(user=request.user)
        .prefetch_related("philosophers")
        .order_by("-created_at")
    )

    # Sadece aktif olanları filtrele
    active_sessions = sessions.filter(status="active")

    return render(request, "symposium/symposium_list.html", {
        "sessions": sessions,
        "active_sessions": active_sessions,  # Şablona aktif oturumları da gönderiyoruz
    })


@login_required
@require_http_methods(["GET", "POST"])
def create_symposium(request):
    philosophers = Philosopher.objects.filter(is_active=True).order_by(
        "display_order", "name"
    )

    if request.method == "POST":
        topic          = request.POST.get("topic", "").strip()
        philosopher_ids = request.POST.getlist("philosophers")
        zeitgeist_mode = request.POST.get("zeitgeist_mode", "classical")

        errors = []
        if not topic:
            errors.append("Tartışma konusu zorunludur.")
        if len(topic) > 500:
            errors.append("Konu 500 karakterden uzun olamaz.")
        if len(philosopher_ids) < 2:
            errors.append("En az 2 filozof seçmelisiniz.")
        if len(philosopher_ids) > 4:
            errors.append("En fazla 4 filozof seçebilirsiniz.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "symposium/create_symposium.html", {
                "philosophers": philosophers,
                "errors": errors,
                "form_data": request.POST,
            })

        selected = Philosopher.objects.filter(pk__in=philosopher_ids, is_active=True)
        session  = SymposiumSession.objects.create(
            user=request.user,
            topic=topic,
            zeitgeist_mode=zeitgeist_mode,
        )
        session.philosophers.set(selected)

        logger.info(
            "Sempozyum oluşturuldu: session=%d, user=%s",
            session.pk, request.user.username,
        )
        return redirect("symposium:chat", session_id=session.pk)

    return render(request, "symposium/create_symposium.html", {
        "philosophers": philosophers,
        "zeitgeist_choices": [
            ("classical", "🏛️ Klasik — Dönemine sadık"),
            ("modern",    "⚡ Modern — Çağdaş yorumla"),
        ],
    })


@login_required
@require_http_methods(["GET"])
def symposium_chat(request, session_id):
    """Ana sempozyum sohbet sayfası."""
    session = get_object_or_404(SymposiumSession, pk=session_id, user=request.user)
    turns   = session.turns.select_related("philosopher").order_by("created_at")
    return render(request, "symposium/symposium_chat.html", {
        "session":     session,
        "philosophers": session.philosopher_list,
        "turns":       turns,
    })


@login_required
@require_http_methods(["GET"])
def symposium_detail(request, session_id):
    """Tamamlanmış sempozyum okuma görünümü."""
    session = get_object_or_404(SymposiumSession, pk=session_id, user=request.user)
    turns   = session.turns.select_related("philosopher").order_by("created_at")
    return render(request, "symposium/symposium_detail.html", {
        "session":     session,
        "turns":       turns,
        "philosophers": session.philosopher_list,
    })


# ── SSE Endpoint'leri ─────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def sse_philosopher_turn(request, session_id):
    """
    Sıradaki filozofu (veya ?philosopher_id=X ile belirtileni) konuşturur.
    SSE stream döner.
    """
    session = get_object_or_404(SymposiumSession, pk=session_id, user=request.user)

    if not session.is_active:
        def already_done():
            yield f"data: {json.dumps({'type':'error','message':'Bu sempozyum tamamlandı.'})}\n\n"
            yield "data: [DONE]\n\n"
        r = StreamingHttpResponse(already_done(), content_type="text/event-stream")
        r["Cache-Control"] = "no-cache"
        r["X-Accel-Buffering"] = "no"
        return r

    philosopher_id = request.GET.get("philosopher_id")
    philosopher_id = int(philosopher_id) if philosopher_id else None

    from .services.symposium_engine import stream_philosopher_turn
    response = StreamingHttpResponse(
        stream_philosopher_turn(session_id=session.pk, philosopher_id=philosopher_id),
        content_type="text/event-stream",
    )
    response["Cache-Control"]     = "no-cache"
    response["X-Accel-Buffering"] = "no"
    # DİKKAT: "Connection": "keep-alive" satırı silindi (WSGI uyumluluğu için)
    return response


@login_required
@require_http_methods(["POST"])
def user_intervene(request, session_id):
    """Kullanıcı araya girer — mesajı kaydeder, JSON döner."""
    session = get_object_or_404(SymposiumSession, pk=session_id, user=request.user)

    try:
        body    = json.loads(request.body)
        content = body.get("message", "").strip()
    except (json.JSONDecodeError, AttributeError):
        content = request.POST.get("message", "").strip()

    if not content:
        return JsonResponse({"error": "Mesaj boş olamaz."}, status=400)
    if len(content) > 2000:
        return JsonResponse({"error": "Mesaj 2000 karakterden uzun olamaz."}, status=400)

    from .services.symposium_engine import save_user_turn
    result = save_user_turn(session_id=session.pk, content=content)
    return JsonResponse({"success": True, **result})


@login_required
@require_http_methods(["GET"])
def sse_summary(request, session_id):
    """Tartışmayı özetler — SSE stream döner."""
    session = get_object_or_404(SymposiumSession, pk=session_id, user=request.user)

    from .services.symposium_engine import stream_summary
    response = StreamingHttpResponse(
        stream_summary(session_id=session.pk),
        content_type="text/event-stream",
    )
    response["Cache-Control"]     = "no-cache"
    response["X-Accel-Buffering"] = "no"
    # DİKKAT: "Connection": "keep-alive" satırı silindi (WSGI uyumluluğu için)
    return response
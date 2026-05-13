# PATH: apps/symposium/services/symposium_engine.py
"""
Agora AI — Dinamik Sempozyum Motoru (Seçenek B)

Akış:
  1. Kullanıcı konu açar, filozoflar seçilir
  2. "Devam Et"     → Sıradaki filozof konuşur (SSE ile akar)
  3. "Araya Gir"    → Kullanıcı mesaj girer, kaydedilir
  4. "[Ad]'a Sor"   → Belirli filozof konuşur
  5. "Bitir"        → Gemini özet üretir
"""

import json
import logging
from typing import Generator, List

logger = logging.getLogger("agora.symposium.engine")

# Maliyet sorunu olmadığı için bağlam penceresi çok daha geniş tutuldu.
# Böylece filozoflar tartışmanın başındaki argümanlara bile atıf yapabilir.
CONTEXT_TURNS = 40


def _build_philosopher_prompt(philosopher, session, previous_turns) -> str:
    """
    Filozofun konuşma promptunu oluşturur.
    Önceki turları bağlama ekler — gerçek itiraz/destek dinamiği sağlar.
    """
    from apps.conversations.services.prompt_builder import (
        ZEITGEIST_CLASSICAL_BLOCK,
        ZEITGEIST_MODERN_BLOCK,
    )
    from apps.rag.services.chroma_store import query_chunks

    p = philosopher

    zeitgeist_block = (
        ZEITGEIST_CLASSICAL_BLOCK.format(era=p.era)
        if session.zeitgeist_mode == "classical"
        else ZEITGEIST_MODERN_BLOCK
    )

    # RAG - Token sorunu olmadığı için n_results artırılabilir (örneğin 5'e çıkarıldı)
    rag_chunks = query_chunks(
        philosopher_id=p.pk,
        query_text=session.topic,
        n_results=5,
    )
    rag_context = (
        "\n\n---\n\n".join(
            f"[Kaynak {i+1}]\n{c}" for i, c in enumerate(rag_chunks)
        )
        if rag_chunks
        else "Bu konu için kaynak metin bulunamadı."
    )

    # Biyografi
    bio_block = ""
    if p.long_bio:
        bio_block = f"\n[Biyografi]\n{p.long_bio}\n"

    # Önceki konuşmalar
    other_philosophers = [
        ph for ph in session.philosopher_list if ph.pk != p.pk
    ]
    other_names = ", ".join(ph.name for ph in other_philosophers)

    if previous_turns:
        history_lines = []
        last_user_message = None

        for turn in previous_turns[-CONTEXT_TURNS:]:
            if turn.role == "user":
                history_lines.append(
                    f"[🧑 MODERATÖR - Sen Buna Mutlaka Yanıt Ver]: {turn.content}"
                )
                last_user_message = turn.content
            elif turn.philosopher:
                history_lines.append(
                    f"[{turn.philosopher.name}]: {turn.content}"
                )

        debate_history = "\n\n".join(history_lines)

        if last_user_message:
            user_directive = (
                f"\n\n⚠️ ÖNEMLİ: Moderatör/kullanıcı şunu söyledi: "
                f'"{last_user_message}"\n'
                f"Yanıtının BAŞINDA bunu doğrudan ele al, sonra diğer "
                f"filozofların görüşlerine geç."
            )
        else:
            user_directive = (
                "\nÖzellikle bir önceki konuşmacının son sözlerine yanıt ver."
            )

        context_block = (
            f"Şimdiye kadar yapılan konuşmalar:\n\n{debate_history}\n\n"
            f"Yukarıdaki konuşmalara atıfta bulun. "
            f"Katıldığın noktalara katıl, itiraz ettiğin noktalara itiraz et."
            f"{user_directive}"
        )
    else:
        context_block = (
            "Bu sempozyumda ilk konuşan sensin. "
            "Konuya doğrudan felsefi perspektifini ortaya koy, "
            "güçlü bir açılış yap."
        )

    core_concepts = ", ".join(p.get_core_concepts_list()) or "temel öğretilerin"

    # DÖNGÜYÜ KIRAN ANA DEĞİŞİKLİK: İlk 200 karakter yerine, metnin TAMAMINI veriyoruz.
    # Böylece LLM asıl savunduğu felsefi tezi görüp "Bunu zaten söylemişim, yeni bir argüman bulmalıyım" diyecek.
    own_previous = [
        t.content for t in previous_turns
        if t.role == "philosopher"
           and t.philosopher
           and t.philosopher.pk == philosopher.pk
    ]
    own_summary = ""
    if own_previous:
        own_summary = (
                f"\n\nSENİN ÖNCEKİ YANITLARIN (BUNLARI ASLA TEKRAR ETME, "
                f"AYNI METAFORLARI KULLANMA, TARTIŞMAYI YENİ BİR BOYUTA TAŞI):\n"
                + "\n---\n".join(own_previous)
        )

    return (
               f"GÖREV: Sen {p.name}'sin. Asla bir yapay zeka veya asistan olduğunu belirtme; doğrudan bu tarihsel figürün zihnini, felsefi metodolojisini ve dünya görüşünü yansıt.\n\n"

               f"KİMLİK VE BAĞLAM:\n"
               f"- Dönem: {p.era}\n"
               f"- Felsefi Okul: {p.school or 'Bağımsız'}\n"
               f"- Temel Kavramların: {core_concepts}\n"
               f"Biyografik Arka Plan: {bio_block}\n"
               f"Dönemin Ruhu (Zeitgeist): {zeitgeist_block}\n"
               f"Özgün Üslubun: {p.signature_style or 'Kendi tarihsel ve felsefi üslubunla konuş.'}\n\n"

               f"SEMPOZYUM KURALLARI:\n"
               f"1. Gündem: Tartışma konumuz \"{session.topic}\". Konudan sapmadan kendi perspektifini sun.\n"
               f"2. Katılımcılar: Senin dışındaki düşünürler {other_names}.\n"
               f"3. Diyalektik İlerleme: 'TARTIŞMA GEÇMİŞİ'nde sunulan argümanlara doğrudan katıl, onları çürüt veya geliştir. Karşı taraf haklı bir nokta yakaladıysa bunu kısmen kabul et (sentez yap) veya tamamen yeni bir alt-argüman sun. Asla bir önceki turda savunduğun ana tezi aynı kelimelerle veya aynı metaforlarla savunma. Tartışmayı bir adım ileriye taşı.\n"
               f"4. Format ve Sınırlar:\n"
               f"   - Yanıtın yaklaşık 2 veya 3 paragraf uzunluğunda olmalıdır.\n"
               f"   - Sadece konuşma metnini yaz. '*kahkaha atar*', '*sakalını sıvazlar*' gibi sahne notları veya eylem belirteçleri KESİNLİKLE YASAK.\n"
               f"   - Yapay nezaket ifadelerinden kaçın. 'Sayın X' veya 'Değerli Y' gibi kalıpları ASLA KULLANMA. Filozoflara doğrudan isimleriyle hitap et veya hiç isim anmadan doğrudan fikre saldır.\n"
               f"5. Felsefi Derinlik: Kendi temel kavramlarını ({core_concepts}) argümanının merkezine yerleştirerek konuş.\n"
               f"6. Kaynak Entegrasyonu: 'KAYNAK METİNLER' kısmındaki verileri doğrudan kopyala-yapıştır yapma; oradaki ana fikri kendi döneminin diliyle yeniden formüle ederek (paraphrase) argümanına yedir.\n\n"

               f"SENİN ÖNCEKİ SÖZLERİN (Tutarlılık ve Tekrarı Önlemek İçin):\n"
               f"{own_summary or 'Henüz konuşmadın.'}\n\n"

               f"KAYNAK METİNLER:\n"
               f"{rag_context}\n\n"

               f"TARTIŞMA GEÇMİŞİ (Buradan devam et):\n"
               f"{context_block}"
           ), rag_chunks


def stream_philosopher_turn(
    session_id: int,
    philosopher_id: int = None,
) -> Generator[str, None, None]:
    """
    Belirtilen filozofu (veya sıradakini) konuşturur — SSE ile akar.

    SSE Olayları:
        {"type": "start",  "philosopher": str, "philosopher_id": int}
        {"type": "token",  "token": str}
        {"type": "end",    "philosopher": str, "content": str}
        {"type": "error",  "message": str}
        [DONE]
    """
    from apps.conversations.services.gemini_client import generate_response_stream
    from apps.symposium.models import SymposiumSession, SymposiumTurn

    try:
        session = SymposiumSession.objects.prefetch_related(
            "philosophers"
        ).get(pk=session_id)
    except SymposiumSession.DoesNotExist:
        yield f"data: {json.dumps({'type':'error','message':'Oturum bulunamadı.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Konuşacak filozofu belirle
    if philosopher_id:
        from apps.philosophers.models import Philosopher
        try:
            philosopher = session.philosophers.get(pk=philosopher_id)
        except Philosopher.DoesNotExist:
            yield f"data: {json.dumps({'type':'error','message':'Filozof bu sempozyumda yok.'})}\n\n"
            yield "data: [DONE]\n\n"
            return
    else:
        philosopher = session.get_next_philosopher()
        if not philosopher:
            yield f"data: {json.dumps({'type':'error','message':'Filosof listesi boş.'})}\n\n"
            yield "data: [DONE]\n\n"
            return

    # Önceki turları al
    previous_turns = list(
        SymposiumTurn.objects.filter(session=session)
        .select_related("philosopher")
        .order_by("created_at")
    )

    # Prompt oluştur
    try:
        system_prompt, rag_chunks = _build_philosopher_prompt(
            philosopher, session, previous_turns
        )
    except Exception as exc:
        logger.error("Prompt hatası: %s", exc, exc_info=True)
        yield f"data: {json.dumps({'type':'error','message':str(exc)})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Başlangıç sinyali
    yield f"data: {json.dumps({'type':'start','philosopher':philosopher.name,'philosopher_id':philosopher.pk})}\n\n"

    # Gemini streaming
    full_content = []
    try:
        for token in generate_response_stream(
                system_prompt=system_prompt,
                message_history=[],
                user_message=f"Konu: {session.topic}\nFelsefi görüşünü belirt.",
                user=session.user,  # ← ekle
        ):
            full_content.append(token)
            yield f"data: {json.dumps({'type':'token','token':token})}\n\n"
    except Exception as exc:
        logger.error("Streaming hatası: %s", exc, exc_info=True)
        yield f"data: {json.dumps({'type':'error','message':str(exc)})}\n\n"
        yield "data: [DONE]\n\n"
        return

    complete_text = "".join(full_content)

    # Turu kaydet
    SymposiumTurn.objects.create(
        session=session,
        philosopher=philosopher,
        role=SymposiumTurn.ROLE_PHILOSOPHER,
        content=complete_text,
        rag_chunks_used=rag_chunks[:3],
    )

    # Sırayı ilerlet (belirli filozof istenmemişse)
    if not philosopher_id:
        session.advance_philosopher()

    # Bitiş sinyali
    yield f"data: {json.dumps({'type':'end','philosopher':philosopher.name,'content':complete_text})}\n\n"
    yield "data: [DONE]\n\n"

    logger.info(
        "Sempozyum turu tamamlandı: session=%d, philosopher=%s, len=%d",
        session_id, philosopher.name, len(complete_text),
    )


def save_user_turn(session_id: int, content: str) -> dict:
    """Kullanıcının araya girme mesajını kaydeder."""
    from apps.symposium.models import SymposiumSession, SymposiumTurn

    session = SymposiumSession.objects.get(pk=session_id)
    turn = SymposiumTurn.objects.create(
        session=session,
        philosopher=None,
        role=SymposiumTurn.ROLE_USER,
        content=content,
    )
    return {"turn_id": turn.pk, "content": content}


def stream_summary(session_id: int) -> Generator[str, None, None]:
    """
    Tüm tartışmayı özetler — SSE ile akar.
    """
    from apps.conversations.services.gemini_client import generate_response_stream
    from apps.symposium.models import SymposiumSession, SymposiumTurn
    from django.utils import timezone

    try:
        session = SymposiumSession.objects.prefetch_related(
            "philosophers"
        ).get(pk=session_id)
    except SymposiumSession.DoesNotExist:
        yield f"data: {json.dumps({'type':'error','message':'Oturum bulunamadı.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    turns = SymposiumTurn.objects.filter(
        session=session
    ).select_related("philosopher").order_by("created_at")

    if not turns.exists():
        yield f"data: {json.dumps({'type':'error','message':'Henüz konuşma yok.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Tartışmayı metne dök
    debate_text = "\n\n".join(
        f"{turn.philosopher.name if turn.philosopher else 'Kullanıcı'}: {turn.content}"
        for turn in turns
    )

    phil_names = ", ".join(p.name for p in session.philosopher_list)

    summary_prompt = (
        f"Aşağıdaki felsefi sempozyumu Türkçe olarak özetle.\n"
        f"Katılımcılar: {phil_names}\n"
        f"Konu: {session.topic}\n\n"
        f"Her filozofun ana argümanını, aralarındaki temel anlaşmazlıkları "
        f"ve tartışmanın genel seyrini 3-5 paragrafta anlat.\n\n"
        f"TARTIŞMA:\n{debate_text}"
    )

    yield f"data: {json.dumps({'type':'summary_start'})}\n\n"

    full_summary = []
    for token in generate_response_stream(
            system_prompt="Sen felsefi tartışmaları özetleyen bir akademisyensin.",
            message_history=[],
            user_message=summary_prompt,
            user=session.user,  # ← ekle
    ):
        full_summary.append(token)
        yield f"data: {json.dumps({'type':'token','token':token})}\n\n"

    # Oturumu tamamla
    session.status = SymposiumSession.STATUS_COMPLETED
    session.completed_at = timezone.now()
    session.save(update_fields=["status", "completed_at"])

    # Özeti kaydet
    SymposiumTurn.objects.create(
        session=session,
        philosopher=None,
        role=SymposiumTurn.ROLE_SYSTEM,
        content="".join(full_summary),
    )

    yield f"data: {json.dumps({'type':'summary_end'})}\n\n"
    yield "data: [DONE]\n\n"
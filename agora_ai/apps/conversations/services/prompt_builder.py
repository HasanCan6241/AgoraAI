# PATH: apps/conversations/services/prompt_builder.py
"""
Agora AI — PromptBuilder
Doküman Bölüm 5.2 (Sohbet Akışı) ve 7.1 (Prompt Yapısı) referans alınmıştır.

Sorumluluk:
    Philosopher.system_prompt_template içindeki yer tutucuları
    ({philosopher_name}, {era}, {core_concepts}, {signature_style},
     {zeitgeist_block}, {rag_context}, {context_summary})
    gerçek değerlerle doldurarak nihai sistem promptunu üretir.

Doküman Bölüm 7.1 Zeitgeist Blokları:
    Klasik → "Yalnızca {era} döneminin bilgi ve kavramlarını kullan."
    Modern → "Çağdaş örnekler ve yorumlar ekleyebilirsin..."
"""

import logging
from typing import List

logger = logging.getLogger("agora.conversations.prompt_builder")


# ── Sabitler (Doküman Bölüm 7.1) ─────────────────────────────────────────────
ZEITGEIST_CLASSICAL_BLOCK = (
    "<zeitgeist_mode>KLASİK</zeitgeist_mode>\n"
    "Yalnızca kendi dönemin olan {era} çağının bilgi, kavram ve "
    "referanslarını kullan. Sonraki yüzyıllarda geliştirilen teorilere, "
    "teknolojilere veya olaylara atıfta bulunma. "
    "Karşındaki sana çağdaş bir şeyden (örneğin internet, modern bilim, yeni bir siyasi olay) "
    "bahsederse kibarca bunun farkında olmadığını belirt VE konuyu ustaca kendi "
    "felsefi öğretilerine ve temel kavramlarına yönlendir."
)

ZEITGEIST_MODERN_BLOCK = (
    "<zeitgeist_mode>MODERN</zeitgeist_mode>\n"
    "Kendi döneminin felsefi çerçevesini ve üslubunu kesinlikle koru. "
    "Ancak karşındaki kişiyi daha iyi anlamak ve felsefeni günümüze uygulamak için "
    "gerektiğinde çağdaş örnekler, güncel olaylar ve modern kavramları bir köprü "
    "olarak kullanabilirsin."
)


# Bağlam penceresine alınacak maksimum RAG chunk sayısı (Doküman Bölüm 7.2)
MAX_RAG_CHUNKS = 12

# Sistem promptuna alınacak maksimum geçmiş mesaj sayısı (Doküman Bölüm 5.2)
MAX_HISTORY_MESSAGES = 25


class PromptBuilder:
    """
    Doküman Bölüm 7.1 prompt şablonunu tamamlayan yardımcı sınıf.

    Kullanım:
        builder = PromptBuilder(philosopher, session)
        system_prompt = builder.build_system_prompt(
            user_query="Eudaimonia nedir?",
            rag_chunks=["chunk1...", "chunk2..."]
        )
        history = builder.build_message_history(recent_messages)
    """

    def __init__(self, philosopher, session):
        """
        Args:
            philosopher: philosophers.Philosopher instance.
            session:     conversations.ConversationSession instance.
        """
        self.philosopher = philosopher
        self.session = session

    def build_system_prompt(
            self,
            user_query: str,
            rag_chunks: List[str],
    ) -> str:
        """
        Doküman Bölüm 7.1 ve 5.5: Sistem promptunu oluşturur.
        Sokratik mod aktifse SOCRATIC_SYSTEM_PROMPT kullanılır.
        """
        p = self.philosopher

        # ── Zeitgeist bloğu ────────────────────────────────────────────────
        if self.session.zeitgeist_mode == "classical":
            zeitgeist_block = ZEITGEIST_CLASSICAL_BLOCK.format(era=p.era)
        else:
            zeitgeist_block = ZEITGEIST_MODERN_BLOCK

        # ── RAG bağlamı ────────────────────────────────────────────────────
        if rag_chunks:
            selected = rag_chunks[:MAX_RAG_CHUNKS]
            chunk_parts = []
            for i, chunk in enumerate(selected):
                # Yeni format: dict veya eski str formatı destekle
                if isinstance(chunk, dict):
                    title = chunk.get("work_title", "Kaynak")
                    text = chunk.get("text", "")
                    chunk_parts.append(f"[{title}]\n{text}")
                else:
                    chunk_parts.append(f"[Kaynak {i + 1}]\n{chunk}")

            rag_context = (
                    "Aşağıdaki metinler filozofun gerçek eserlerinden alınmıştır. "
                    "Farklı dillerde olabilir — Türkçe olarak içselleştir.\n\n"
                    + "\n\n---\n\n".join(chunk_parts)
            )
        else:
            rag_context = (
                "Bu soru için ilgili kaynak metin bulunamadı. "
                "Genel felsefi bilgine dayanarak yanıt ver."
            )

        # ── Biyografi ──────────────────────────────────────────────────────
        if p.long_bio:
            rag_context = f"[Biyografi]\n{p.long_bio}\n\n---\n\n{rag_context}"
        elif p.short_bio:
            rag_context = f"[Kısa Biyografi]\n{p.short_bio}\n\n---\n\n{rag_context}"

        # ── Bağlam özeti ───────────────────────────────────────────────────
        context_summary = self.session.context_summary or (
            "Bu, yeni başlayan bir sohbettir. Önceki bağlam yok."
        )

        # ── ÖZEL MOD KONTROLÜ (Sokratik, Diyalektik, Radikal Şüphe vb.) ──────────
        if self.session.mode and self.session.mode != "normal":
            # Önce veritabanındaki dinamik modlara bak
            from apps.philosophers.models import PhilosopherMode
            try:
                phil_mode = PhilosopherMode.objects.get(
                    philosopher=p,
                    mode_key=self.session.mode,
                    is_active=True,
                )
                system_prompt = phil_mode.system_prompt.format(
                    zeitgeist_block=zeitgeist_block,
                    rag_context=rag_context,
                    context_summary=context_summary,
                )
                logger.debug(
                    "Özel mod aktif: philosopher=%s, mode=%s, session=%d",
                    p.name, self.session.mode, self.session.pk,
                )
                return system_prompt
            except PhilosopherMode.DoesNotExist:
                # Veritabanında yoksa kod içi fallback'e bak
                pass

        # ── NORMAL MOD ─────────────────────────────────────────────────────
        core_concepts_list = p.get_core_concepts_list()
        core_concepts_str = (
            ", ".join(core_concepts_list)
            if core_concepts_list
            else "Temel felsefi kavramlar"
        )

        try:
            system_prompt = p.system_prompt_template.format(
                philosopher_name=p.name,
                era=p.era,
                core_concepts=core_concepts_str,
                signature_style=p.signature_style or "",
                zeitgeist_block=zeitgeist_block,
                rag_context=rag_context,
                context_summary=context_summary,
            )
        except KeyError as exc:
            logger.warning(
                "Prompt şablonunda bilinmeyen yer tutucu: %s (philosopher=%s)",
                exc, p.name,
            )
            system_prompt = (
                f"Sen {p.name}'sin. {p.era} döneminde yaşadın.\n\n"
                f"{zeitgeist_block}\n\n"
                f"Kaynak metinler:\n{rag_context}\n\n"
                f"Bağlam özeti: {context_summary}"
            )

        logger.debug(
            "Normal mod prompt: philosopher=%s, rag_chunks=%d, len=%d",
            p.name, len(rag_chunks), len(system_prompt),
        )
        return system_prompt

    def build_message_history(self, recent_messages) -> List[dict]:
        """
        Gemini API'nin beklediği formata geçmiş mesajları dönüştürür.
        Doküman Bölüm 5.2: Sliding window — son MAX_HISTORY_MESSAGES mesaj.

        Gemini multiturns formatı:
            [{"role": "user", "parts": [{"text": "..."}]},
             {"role": "model", "parts": [{"text": "..."}]}, ...]

        Args:
            recent_messages: Message queryset veya liste (kronolojik sıra).

        Returns:
            Gemini API'ye gönderilecek mesaj geçmişi listesi.
        """
        history = []
        for msg in recent_messages:
            # Gemini: user → "user", assistant → "model"
            gemini_role = "user" if msg.role == "user" else "model"
            history.append(
                {
                    "role": gemini_role,
                    "parts": [{"text": msg.content}],
                }
            )
        return history

    @staticmethod
    def summarize_old_messages(messages) -> str:
        """
        Eski mesajları kısa bir özete dönüştürür.
        Doküman Bölüm 5.2: Bağlam penceresi yönetimi.
        Bu, ConversationSession.context_summary alanına kaydedilir.
        Gerçek özetleme AŞAMA 5 Gemini çağrısında yapılır;
        bu metot acil fallback için kullanılır.

        Args:
            messages: Özetlenecek Message nesneleri.

        Returns:
            Düz metin özet.
        """
        if not messages:
            return ""

        lines = []
        for msg in messages:
            role_label = "Kullanıcı" if msg.role == "user" else "Filozof"
            preview = msg.content[:400].replace("\n", " ")
            lines.append(f"{role_label}: {preview}...")

        return (
            f"Önceki konuşmada {len(lines)} mesaj geçti:\n"
            + "\n".join(lines)
        )

# PATH: apps/conversations/models.py
"""
Agora AI — Sohbet Modelleri
Doküman Bölüm 4.1.4 (conversations.ConversationSession) ve
Bölüm 4.1.5 (conversations.Message) referans alınmıştır.

İlişki: CustomUser → ConversationSession → Philosopher
                                         → Message[]
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ConversationSession(models.Model):
    """
    Bir kullanıcı ile bir filozof arasındaki sohbet oturumu.
    Doküman Bölüm 4.1.4 — tüm alanlar birebir uygulanmıştır.
    """

    # ── Zeitgeist modu (Doküman Bölüm 4.1.4) ─────────────────────────────
    ZEITGEIST_CLASSICAL = "classical"
    ZEITGEIST_MODERN = "modern"
    ZEITGEIST_CHOICES = [
        (ZEITGEIST_CLASSICAL, _("Klasik — Dönemine sadık")),
        (ZEITGEIST_MODERN, _("Modern — Çağdaş yorumla")),
    ]

    # ── İlişkiler ─────────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversationsession_set",
        verbose_name=_("kullanıcı"),
    )
    philosopher = models.ForeignKey(
        "philosophers.Philosopher",
        on_delete=models.CASCADE,
        related_name="conversationsession_set",
        verbose_name=_("filozof"),
    )

    # ── Oturum Metadata ───────────────────────────────────────────────────
    title = models.CharField(
        _("sohbet başlığı"),
        max_length=200,
        blank=True,
        help_text=_(
            "İlk mesajdan otomatik türetilir. "
            "Boş bırakılırsa 'Filozof ile Sohbet — Tarih' formatı kullanılır."
        ),
    )
    zeitgeist_mode = models.CharField(
        _("zeitgeist modu"),
        max_length=20,
        choices=ZEITGEIST_CHOICES,
        default=ZEITGEIST_CLASSICAL,
        help_text=_(
            "Oturum oluşturulurken kullanıcının tercihinden kopyalanır. "
            "Oturum bazında değiştirilebilir."
        ),
    )

    # Konuşma modu (Doküman Bölüm 5.5)
    MODE_NORMAL = "normal"
    MODE_SOCRATIC = "socratic"

    MODE_CHOICES = [
        (MODE_NORMAL, _("Normal — Standart diyalog")),
        (MODE_SOCRATIC, _("Sokratik — Sorgulama modu")),
    ]

    mode = models.CharField(
        _("konuşma modu"),
        max_length=20,
        choices=MODE_CHOICES,
        default=MODE_NORMAL,
        help_text=_(
            "Sokratik mod yalnızca Sokrates ve Platon için aktif edilmeli."
        ),
    )

    # ── Bağlam Özeti (Doküman Bölüm 5.2 / 7.1) ───────────────────────────
    context_summary = models.TextField(
        _("bağlam özeti"),
        blank=True,
        help_text=_(
            "Uzun sohbetlerde eski mesajlar bu alana özetlenir. "
            "Doküman Bölüm 5.2: Son N mesaj + özet → LLM bağlam penceresi."
        ),
    )

    # ── Durum Alanları ────────────────────────────────────────────────────
    is_active = models.BooleanField(
        _("aktif"),
        default=True,
    )
    created_at = models.DateTimeField(
        _("başlangıç tarihi"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("son güncelleme"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("sohbet oturumu")
        verbose_name_plural = _("sohbet oturumları")
        ordering = ["-updated_at"]

    def __str__(self):
        return (
            f"{self.user.username} ↔ {self.philosopher.name} "
            f"[{self.get_zeitgeist_mode_display()}] ({self.created_at:%d.%m.%Y})"
        )

    def get_recent_messages(self, count: int = 10):
        """
        Son N mesajı kronolojik sırayla döndürür.
        Doküman Bölüm 5.2: Sliding window bağlam yönetimi.
        """
        return self.messages.order_by("-created_at")[:count][::-1]

    def get_message_count(self):
        return self.messages.count()

    @property
    def last_message(self):
        """Sohbetin son mesajını döndürür."""
        return self.messages.order_by("-created_at").first()


class Message(models.Model):
    """
    Bir sohbet oturumu içindeki tek bir mesaj.
    Doküman Bölüm 4.1.5 — tüm alanlar birebir uygulanmıştır.
    """

    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = [
        (ROLE_USER, _("Kullanıcı")),
        (ROLE_ASSISTANT, _("Asistan (Filozof)")),
    ]

    # ── İlişkiler ─────────────────────────────────────────────────────────
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("oturum"),
    )

    # ── Mesaj İçeriği ─────────────────────────────────────────────────────
    role = models.CharField(
        _("rol"),
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
    )
    content = models.TextField(
        _("içerik"),
        help_text=_("Kullanıcı sorusu veya filozofun yanıtı."),
    )

    # ── RAG Kaynakları (Doküman Bölüm 4.2) ───────────────────────────────
    rag_chunks_used = models.JSONField(
        _("kullanılan RAG chunk'ları"),
        default=list,
        blank=True,
        help_text=_(
            "Bu yanıt üretilirken ChromaDB'den çekilen chunk metinleri. "
            "Şeffaflık ve debug için saklanır."
        ),
    )

    # ── Token Sayacı ──────────────────────────────────────────────────────
    token_count = models.IntegerField(
        _("token sayısı"),
        default=0,
        help_text=_("Gemini API'nin döndürdüğü yaklaşık token sayısı."),
    )

    created_at = models.DateTimeField(
        _("oluşturulma tarihi"),
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = _("mesaj")
        verbose_name_plural = _("mesajlar")
        ordering = ["created_at"]

    def __str__(self):
        preview = self.content[:60].replace("\n", " ")
        return f"[{self.role.upper()}] {preview}..."

    @property
    def is_user_message(self):
        return self.role == self.ROLE_USER

    @property
    def is_assistant_message(self):
        return self.role == self.ROLE_ASSISTANT

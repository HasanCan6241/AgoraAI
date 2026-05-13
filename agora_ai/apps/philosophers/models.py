# PATH: apps/philosophers/models.py
"""
Agora AI — Filozof Modelleri
Doküman Bölüm 4.1.2 (philosophers.Philosopher) ve
Bölüm 4.1.3 (philosophers.PhilosophicalWork) referans alınmıştır.
"""

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Philosopher(models.Model):
    """
    Bir filozofu ve onun LLM persona şablonunu temsil eder.
    Doküman Bölüm 4.1.2 — tüm alanlar birebir uygulanmıştır.
    """

    # ── Temel Bilgiler ────────────────────────────────────────────────────
    name = models.CharField(
        _("tam ad"),
        max_length=100,
        help_text=_("Filozofun tam adı (ör: 'Immanuel Kant')"),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=100,
        unique=True,
        help_text=_("URL dostu isim (ör: 'immanuel-kant'). Otomatik oluşturulabilir."),
    )
    era = models.CharField(
        _("dönem"),
        max_length=100,
        help_text=_("Yaşadığı dönem (ör: 'Antik Çağ, MÖ 470–399')"),
    )
    school = models.CharField(
        _("felsefi okul"),
        max_length=100,
        blank=True,
        help_text=_("Ait olduğu felsefi akım (ör: 'Alman İdealizmi')"),
    )

    # ── Biyografi ─────────────────────────────────────────────────────────
    short_bio = models.TextField(
        _("kısa biyografi"),
        help_text=_("Profil kartında gösterilen kısa tanıtım metni."),
    )
    long_bio = models.TextField(
        _("detaylı biyografi"),
        blank=True,
        help_text=_("Profil sayfasında gösterilen kapsamlı biyografi."),
    )

    # ── Felsefi İçerik ────────────────────────────────────────────────────
    core_concepts = models.JSONField(
        _("temel kavramlar"),
        default=list,
        blank=True,
        help_text=_(
            "Filozofun öne çıkan kavramları. JSON dizisi olarak girin: "
            '["Kategorik Buyrucu", "A Priori", "Fenomen"]'
        ),
    )
    signature_style = models.TextField(
        _("imza üslubu"),
        blank=True,
        help_text=_(
            "Filozofun dil ve düşünce üslubunun tanımı. "
            "LLM persona prompt'una aktarılır."
        ),
    )

    # ── LLM Persona Şablonu (Doküman Bölüm 7.1) ──────────────────────────
    system_prompt_template = models.TextField(
        _("sistem prompt şablonu"),
        help_text=_(
            "LLM'e verilecek ana persona şablonu. "
            "{philosopher_name}, {era}, {core_concepts}, {signature_style}, "
            "{zeitgeist_block}, {rag_context}, {context_summary} "
            "yer tutucularını kullanabilirsiniz."
        ),
    )

    # ── Görsel ────────────────────────────────────────────────────────────
    avatar_image = models.ImageField(
        _("avatar görseli"),
        upload_to="philosophers/avatars/",
        blank=True,
        null=True,
        help_text=_("Filozofun portre görseli (tercihen kare format)."),
    )

    # ── Yönetim Alanları ──────────────────────────────────────────────────
    is_active = models.BooleanField(
        _("aktif"),
        default=True,
        help_text=_("Pasif filozoflar kullanıcılara gösterilmez."),
    )
    display_order = models.IntegerField(
        _("sıralama önceliği"),
        default=0,
        help_text=_("Küçük sayı önce listelenir."),
    )

    class Meta:
        verbose_name = _("filozof")
        verbose_name_plural = _("filozoflar")
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.era})"

    def get_absolute_url(self):
        return reverse("philosophers:detail", kwargs={"slug": self.slug})

    def get_core_concepts_list(self):
        """core_concepts JSON alanını Python listesi olarak döndürür."""
        if isinstance(self.core_concepts, list):
            return self.core_concepts
        return []

    @property
    def avatar_url(self):
        """Avatar URL'ini ya da varsayılan yer tutucuyu döndürür."""
        if self.avatar_image:
            return self.avatar_image.url
        return None

    @property
    def work_count(self):
        """Sisteme yüklenmiş tamamlanmış eser sayısını döndürür."""
        return self.works.filter(ingestion_status="completed").count()


class PhilosophicalWork(models.Model):
    """
    Bir filozofa ait felsefi eseri temsil eder.
    Doküman Bölüm 4.1.3 — tüm alanlar birebir uygulanmıştır.
    """

    # ── İşleme Durumu Seçenekleri ─────────────────────────────────────────
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    INGESTION_STATUS_CHOICES = [
        (STATUS_PENDING, _("Bekliyor")),
        (STATUS_PROCESSING, _("İşleniyor")),
        (STATUS_COMPLETED, _("Tamamlandı")),
        (STATUS_FAILED, _("Başarısız")),
    ]

    # ── İlişkiler ─────────────────────────────────────────────────────────
    philosopher = models.ForeignKey(
        Philosopher,
        on_delete=models.CASCADE,
        related_name="works",
        verbose_name=_("filozof"),
    )

    # ── Eser Bilgileri ────────────────────────────────────────────────────
    title = models.CharField(
        _("eser başlığı"),
        max_length=200,
        help_text=_("Eserin tam başlığı."),
    )
    original_file = models.FileField(
        _("kaynak dosya"),
        upload_to="philosophical_works/",
        blank=True,
        null=True,
        help_text=_(
            "Yüklenecek PDF veya TXT dosyası. "
            "Doküman Bölüm 7.4: Yalnızca .pdf ve .txt, max 50MB."
        ),
    )

    # ── Ingestion Durumu (Doküman Bölüm 4.1.3) ───────────────────────────
    ingestion_status = models.CharField(
        _("işleme durumu"),
        max_length=20,
        choices=INGESTION_STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    ingestion_error = models.TextField(
        _("hata mesajı"),
        blank=True,
        help_text=_("İşleme başarısız olduğunda hata detayı buraya kaydedilir."),
    )
    chunk_count = models.IntegerField(
        _("chunk sayısı"),
        default=0,
        help_text=_("RAG için oluşturulan metin parçası sayısı."),
    )

    # ── Tarihler ──────────────────────────────────────────────────────────
    created_at = models.DateTimeField(
        _("yükleme tarihi"),
        auto_now_add=True,
    )
    completed_at = models.DateTimeField(
        _("tamamlanma tarihi"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("felsefi eser")
        verbose_name_plural = _("felsefi eserler")
        ordering = ["philosopher", "title"]

    def __str__(self):
        return f"{self.philosopher.name} — {self.title} [{self.get_ingestion_status_display()}]"

    @property
    def is_ready(self):
        """Eser RAG sorgularına hazır mı?"""
        return self.ingestion_status == self.STATUS_COMPLETED

    def validate_file_extension(self):
        """
        Doküman Bölüm 7.4: Yalnızca .pdf ve .txt dosyası kabul et.
        Admin ve form katmanında çağrılır.
        """
        import os

        if self.original_file:
            ext = os.path.splitext(self.original_file.name)[1].lower()
            if ext not in [".pdf", ".txt"]:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    _("Yalnızca .pdf ve .txt dosyaları kabul edilmektedir.")
                )

class PhilosopherMode(models.Model):
    """
    Bir filozofa özgü özel konuşma modu.
    Her mod için ayrı sistem promptu ve UI etiketi tanımlanır.
    Yeni mod eklemek için yalnızca bu tabloya kayıt eklenir.
    """

    philosopher = models.ForeignKey(
        Philosopher,
        on_delete=models.CASCADE,
        related_name="special_modes",
        verbose_name=_("filozof"),
    )
    mode_key = models.CharField(
        _("mod anahtarı"),
        max_length=50,
        help_text=_(
            "URL ve kod içinde kullanılan benzersiz anahtar. "
            "ör: 'socratic', 'dialectic', 'radical_doubt'"
        ),
    )
    display_name = models.CharField(
        _("görünen ad"),
        max_length=100,
        help_text=_("ör: 'Sokratik Sorgulama Modu'"),
    )
    button_label = models.CharField(
        _("buton etiketi"),
        max_length=80,
        help_text=_("ör: '🔍 Sokratik Mod'"),
    )
    button_description = models.CharField(
        _("buton açıklaması"),
        max_length=150,
        blank=True,
        help_text=_("ör: 'Sorgulanarak öğren'"),
    )
    system_prompt = models.TextField(
        _("sistem promptu"),
        help_text=_(
            "Bu mod için tam sistem promptu. "
            "Kullanılabilir yer tutucular: "
            "{zeitgeist_block}, {rag_context}, {context_summary}"
        ),
    )
    is_default = models.BooleanField(
        _("varsayılan mod"),
        default=False,
        help_text=_(
            "Bu filozofun profil sayfasında ilk/öne çıkan buton olarak göster."
        ),
    )
    is_active = models.BooleanField(_("aktif"), default=True)
    display_order = models.IntegerField(_("sıralama"), default=0)

    class Meta:
        verbose_name = _("filozof modu")
        verbose_name_plural = _("filozof modları")
        ordering = ["display_order"]
        unique_together = [("philosopher", "mode_key")]

    def __str__(self):
        return f"{self.philosopher.name} — {self.display_name}"
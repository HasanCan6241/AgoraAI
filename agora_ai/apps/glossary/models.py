# PATH: apps/glossary/models.py
"""
Agora AI — Kavram Sözlüğü Modeli
Doküman Bölüm 6/AŞAMA 6: Felsefi kavramları ve tanımlarını saklar.
Her kavram bir veya daha fazla filozofla ilişkilendirilebilir.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class PhilosophicalConcept(models.Model):
    """
    Felsefi bir kavram ve açıklaması.
    Kullanıcılar sohbet sırasında kavramların üzerine tıklayıp
    tanımını görebilir (tooltip veya modal).
    """

    name = models.CharField(
        _("kavram adı"),
        max_length=150,
        unique=True,
        help_text=_("Kavramın orijinal ya da Türkçe adı. ör: 'Kategorik Buyruç'"),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=150,
        unique=True,
        help_text=_("URL dostu ad. Otomatik türetilebilir."),
    )
    original_term = models.CharField(
        _("özgün terim"),
        max_length=150,
        blank=True,
        help_text=_("Kavramın özgün dilindeki adı. ör: 'Kategorischer Imperativ'"),
    )
    philosophers = models.ManyToManyField(
        "philosophers.Philosopher",
        related_name="concepts",
        blank=True,
        verbose_name=_("ilişkili filozoflar"),
    )
    short_definition = models.TextField(
        _("kısa tanım"),
        help_text=_("1-2 cümlelik özet. Tooltip olarak gösterilir."),
    )
    long_definition = models.TextField(
        _("ayrıntılı açıklama"),
        blank=True,
        help_text=_("Kavramın felsefi bağlamda kapsamlı açıklaması."),
    )
    related_concepts = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
        verbose_name=_("ilişkili kavramlar"),
    )
    is_active = models.BooleanField(_("aktif"), default=True)
    created_at = models.DateTimeField(_("oluşturulma tarihi"), auto_now_add=True)

    class Meta:
        verbose_name = _("felsefi kavram")
        verbose_name_plural = _("felsefi kavramlar")
        ordering = ["name"]

    def __str__(self):
        return self.name

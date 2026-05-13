# PATH: apps/symposium/models.py
"""
Agora AI — Sempozyum Modelleri (Dinamik Tartışma — Seçenek B)
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class SymposiumSession(models.Model):
    STATUS_ACTIVE    = "active"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED    = "failed"

    STATUS_CHOICES = [
        (STATUS_ACTIVE,    _("Aktif")),
        (STATUS_COMPLETED, _("Tamamlandı")),
        (STATUS_FAILED,    _("Başarısız")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="symposiumsession_set",
        verbose_name=_("kullanıcı"),
    )
    philosophers = models.ManyToManyField(
        "philosophers.Philosopher",
        related_name="symposium_sessions",
        verbose_name=_("katılımcı filozoflar"),
    )
    topic = models.TextField(_("tartışma konusu"))
    zeitgeist_mode = models.CharField(
        _("zeitgeist modu"), max_length=20,
        choices=[("classical", _("Klasik")), ("modern", _("Modern"))],
        default="classical",
    )
    status = models.CharField(
        _("durum"), max_length=20,
        choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True,
    )
    current_philosopher_index = models.IntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("sempozyum oturumu")
        verbose_name_plural = _("sempozyum oturumları")
        ordering = ["-created_at"]

    def __str__(self):
        names = ", ".join(p.name for p in self.philosophers.all()[:3])
        return f"Sempozyum [{names}] — {self.topic[:50]}"

    @property
    def philosopher_list(self):
        return list(self.philosophers.all().order_by("display_order", "name"))

    @property
    def turn_count(self):
        return self.turns.count()

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    def get_next_philosopher(self):
        phils = self.philosopher_list
        if not phils:
            return None
        idx = self.current_philosopher_index % len(phils)
        return phils[idx]

    def advance_philosopher(self):
        phils = self.philosopher_list
        if phils:
            self.current_philosopher_index = (
                self.current_philosopher_index + 1
            ) % len(phils)
            self.save(update_fields=["current_philosopher_index"])


def reactivate(self):
    """Admin panelinden sempozyumu tekrar aktif hale getirir."""
    self.status = self.STATUS_ACTIVE
    self.completed_at = None
    self.save(update_fields=["status", "completed_at"])

class SymposiumTurn(models.Model):
    ROLE_PHILOSOPHER = "philosopher"
    ROLE_USER        = "user"
    ROLE_SYSTEM      = "system"

    ROLE_CHOICES = [
        (ROLE_PHILOSOPHER, _("Filozof")),
        (ROLE_USER,        _("Kullanıcı")),
        (ROLE_SYSTEM,      _("Sistem")),
    ]

    session = models.ForeignKey(
        SymposiumSession, on_delete=models.CASCADE,
        related_name="turns", verbose_name=_("oturum"),
    )
    philosopher = models.ForeignKey(
        "philosophers.Philosopher", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="symposium_turns",
    )
    role            = models.CharField(_("rol"), max_length=20, choices=ROLE_CHOICES)
    content         = models.TextField(_("içerik"))
    rag_chunks_used = models.JSONField(default=list, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("sempozyum turu")
        verbose_name_plural = _("sempozyum turları")
        ordering = ["created_at"]

    def __str__(self):
        who = self.philosopher.name if self.philosopher else "Kullanıcı"
        return f"{who}: {self.content[:60]}..."
# PATH: apps/accounts/models.py
"""
Agora AI — Özel Kullanıcı Modeli
Doküman Bölüm 4.1.1 (accounts.CustomUser) referans alınmıştır.

Alan listesi:
    id, email, username, password, preferred_language,
    zeitgeist_mode, created_at, is_active
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """
    CustomUser için özel manager.
    Email birincil kimlik alanı olarak kullanılır (username değil).
    """

    def create_user(self, email, username, password=None, **extra_fields):
        """Standart kullanıcı oluşturur."""
        if not email:
            raise ValueError(_("E-posta adresi zorunludur."))
        if not username:
            raise ValueError(_("Kullanıcı adı zorunludur."))

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """Süper kullanıcı (admin) oluşturur."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Süper kullanıcı is_staff=True olmalıdır."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Süper kullanıcı is_superuser=True olmalıdır."))

        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Agora AI özel kullanıcı modeli.
    Doküman Bölüm 4.1.1 — tüm alanlar birebir uygulanmıştır.
    Giriş kimliği: email (username değil).
    """

    # Doküman: zeitgeist_mode seçenekleri
    ZEITGEIST_CHOICES = [
        ("classical", "Klasik — Dönemine sadık"),
        ("modern", "Modern — Çağdaş yorumla"),
    ]

    # Doküman: preferred_language seçenekleri
    LANGUAGE_CHOICES = [
        ("tr", "Türkçe"),
        ("en", "English"),
        ("de", "Deutsch"),
        ("fr", "Français"),
    ]

    deepseek_api_key = models.CharField(
        _("DeepSeek API anahtarı"),
        max_length=200,
        blank=True,
        help_text=_(
            "Kendi DeepSeek API anahtarınız. "
            "https://platform.deepseek.com/api_keys adresinden alabilirsiniz."
        ),
    )

    # ── Temel Alanlar (Doküman Bölüm 4.1.1) ─────────────────────────────
    email = models.EmailField(
        _("e-posta adresi"),
        unique=True,
        max_length=254,
        help_text=_("Giriş için kullanılan benzersiz e-posta adresi."),
    )
    username = models.CharField(
        _("kullanıcı adı"),
        max_length=50,
        unique=True,
        help_text=_("Platformda görünen ad. En fazla 50 karakter."),
    )
    preferred_language = models.CharField(
        _("tercih edilen dil"),
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default="tr",
    )
    zeitgeist_mode = models.CharField(
        _("zeitgeist modu"),
        max_length=20,
        choices=ZEITGEIST_CHOICES,
        default="classical",
        help_text=_(
            "Klasik: Filozoflar yalnızca kendi dönemlerinin bilgisiyle yanıt verir. "
            "Modern: Çağdaş yorumlar ve güncel örnekler içerebilir."
        ),
    )
    created_at = models.DateTimeField(
        _("kayıt tarihi"),
        auto_now_add=True,
    )

    # ── Django Auth Alanları ──────────────────────────────────────────────
    is_active = models.BooleanField(
        _("aktif"),
        default=True,
        help_text=_("Bu seçeneğin işareti kaldırıldığında hesap devre dışı kalır."),
    )
    is_staff = models.BooleanField(
        _("personel"),
        default=False,
        help_text=_("Bu kullanıcının admin paneline erişip erişemeyeceğini belirler."),
    )

    objects = CustomUserManager()

    # Email ile giriş yapılır
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("kullanıcı")
        verbose_name_plural = _("kullanıcılar")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} <{self.email}>"

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

# PATH: apps/accounts/forms.py
"""
Agora AI — Hesap Formları
Doküman Bölüm 5.1 (Kullanıcı Kaydı ve Onboarding Akışı) referans alınmıştır.
"""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


class RegisterForm(forms.ModelForm):
    """
    Yeni kullanıcı kayıt formu.
    Doküman Akış 5.1: email unique kontrolü + şifre gücü validasyonu.
    """

    password1 = forms.CharField(
        label=_("Şifre"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "En az 8 karakter",
                "autocomplete": "new-password",
            }
        ),
        help_text=_("En az 8 karakter, yalnızca rakamlardan oluşmamalı."),
    )
    password2 = forms.CharField(
        label=_("Şifre Tekrarı"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Şifrenizi tekrar girin",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = CustomUser
        fields = ["email", "username", "preferred_language", "zeitgeist_mode"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "ornek@eposta.com",
                    "autocomplete": "email",
                }
            ),
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Görünen adınız",
                    "autocomplete": "username",
                }
            ),
            "preferred_language": forms.Select(
                attrs={"class": "form-select"}
            ),
            "zeitgeist_mode": forms.Select(
                attrs={"class": "form-select"}
            ),
        }
        labels = {
            "email": _("E-posta Adresi"),
            "username": _("Kullanıcı Adı"),
            "preferred_language": _("Tercih Edilen Dil"),
            "zeitgeist_mode": _("Varsayılan Zeitgeist Modu"),
        }

    def clean_email(self):
        """Doküman Akış 5.1: email unique kontrolü."""
        email = self.cleaned_data.get("email", "").lower()
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError(
                _("Bu e-posta adresi zaten kayıtlı. Giriş yapmayı deneyin.")
            )
        return email

    def clean_username(self):
        """Kullanıcı adı benzersizlik ve karakter kontrolü."""
        username = self.cleaned_data.get("username", "").strip()
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise ValidationError(
                _("Bu kullanıcı adı zaten alınmış. Farklı bir ad seçin.")
            )
        if len(username) < 3:
            raise ValidationError(
                _("Kullanıcı adı en az 3 karakter olmalıdır.")
            )
        return username

    def clean_password1(self):
        """Django'nun yerleşik şifre validatörlerini çalıştır."""
        password = self.cleaned_data.get("password1")
        if password:
            validate_password(password)
        return password

    def clean(self):
        """İki şifre alanının eşleştiğini doğrula."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error(
                "password2",
                _("Şifreler eşleşmiyor. Lütfen tekrar deneyin."),
            )
        return cleaned_data

    def save(self, commit=True):
        """Doküman Akış 5.1: CustomUser.objects.create_user() çağrısı."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.email = self.cleaned_data["email"].lower()
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """
    Kullanıcı giriş formu.
    Giriş kimliği: email (Doküman Bölüm 4.1.1 — USERNAME_FIELD = 'email').
    """

    email = forms.EmailField(
        label=_("E-posta Adresi"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "ornek@eposta.com",
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label=_("Şifre"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Şifreniz",
                "autocomplete": "current-password",
            }
        ),
    )
    remember_me = forms.BooleanField(
        label=_("Beni hatırla"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").lower()
        password = cleaned_data.get("password")

        if email and password:
            self.user_cache = authenticate(
                self.request, username=email, password=password
            )
            if self.user_cache is None:
                raise ValidationError(
                    _("E-posta adresi veya şifre hatalı. Lütfen tekrar deneyin.")
                )
            if not self.user_cache.is_active:
                raise ValidationError(
                    _("Bu hesap devre dışı bırakılmıştır.")
                )
        return cleaned_data

    def get_user(self):
        return self.user_cache


class ProfileUpdateForm(forms.ModelForm):
    """
    Kullanıcı profil güncelleme formu.
    Şifre değişikliği bu formda yer almaz; ayrı bir endpoint ile yapılır.
    """

    class Meta:
        model = CustomUser
        fields = ["username", "preferred_language", "zeitgeist_mode", "deepseek_api_key"]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "preferred_language": forms.Select(
                attrs={"class": "form-select"}
            ),
            "zeitgeist_mode": forms.Select(
                attrs={"class": "form-select"}
            ),
            "deepseek_api_key": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "sk-...",
                    "autocomplete": "off",
                }

            ),
        }
        labels = {
            "username": _("Kullanıcı Adı"),
            "preferred_language": _("Tercih Edilen Dil"),
            "zeitgeist_mode": _("Varsayılan Zeitgeist Modu"),
            "deepseek_api_key": _("DeepSeek API Anahtarı"),
        }

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        qs = CustomUser.objects.filter(username__iexact=username)
        # Mevcut kullanıcıyı hariç tut
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                _("Bu kullanıcı adı zaten alınmış.")
            )
        if len(username) < 3:
            raise ValidationError(
                _("Kullanıcı adı en az 3 karakter olmalıdır.")
            )
        return username

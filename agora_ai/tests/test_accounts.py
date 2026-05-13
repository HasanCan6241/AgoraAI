# PATH: tests/test_accounts.py
"""
Agora AI — Hesap Testleri
Doküman Bölüm 6/AŞAMA 7: accounts app birim ve entegrasyon testleri.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


# ── Model Testleri ────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestCustomUser:
    """CustomUser model testleri."""

    def test_create_user_with_email(self):
        """Email birincil kimlik olarak kullanılmalı."""
        user = User.objects.create_user(
            email="kant@agora.ai",
            username="kant",
            password="CategoricalImperative1!",
        )
        assert user.email == "kant@agora.ai"
        assert user.username == "kant"
        assert user.check_password("CategoricalImperative1!")
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_superuser(self):
        """Süper kullanıcı is_staff ve is_superuser olmalı."""
        admin = User.objects.create_superuser(
            email="admin@agora.ai",
            username="admin",
            password="AdminPass123!",
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_str_representation(self, user):
        """__str__ 'username <email>' formatında olmalı."""
        assert "testuser" in str(user)
        assert "test@agora.ai" in str(user)

    def test_default_zeitgeist_mode(self, user):
        """Varsayılan zeitgeist modu 'classical' olmalı."""
        assert user.zeitgeist_mode == "classical"

    def test_default_preferred_language(self, user):
        """Varsayılan dil 'tr' olmalı."""
        assert user.preferred_language == "tr"

    def test_email_uniqueness(self, user):
        """Aynı email ile ikinci kullanıcı oluşturulamaz."""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="test@agora.ai",  # Zaten var
                username="another",
                password="AnotherPass123!",
            )

    def test_create_user_without_email_raises(self):
        """Email olmadan kullanıcı oluşturmak ValueError fırlatmalı."""
        with pytest.raises(ValueError, match="E-posta adresi zorunludur"):
            User.objects.create_user(
                email="",
                username="noemail",
                password="Pass123!",
            )


# ── View Testleri ─────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestRegisterView:
    """Kayıt görünümü testleri."""

    def test_register_page_loads(self, client):
        """Kayıt sayfası GET isteğine 200 döndürmeli."""
        url = reverse("accounts:register")
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"Agora" in resp.content

    def test_register_creates_user(self, client):
        """Geçerli form verisiyle kullanıcı oluşturulmalı."""
        url = reverse("accounts:register")
        resp = client.post(url, {
            "email":             "nietzsche@agora.ai",
            "username":          "nietzsche",
            "password1":         "WillToPower123!",
            "password2":         "WillToPower123!",
            "preferred_language": "tr",
            "zeitgeist_mode":    "classical",
        })
        assert resp.status_code == 302  # Redirect
        assert User.objects.filter(email="nietzsche@agora.ai").exists()

    def test_register_redirect_after_success(self, client):
        """Başarılı kayıt /philosophers/'a yönlendirmeli."""
        url = reverse("accounts:register")
        resp = client.post(url, {
            "email":             "platon@agora.ai",
            "username":          "platon",
            "password1":         "AcademiaPass123!",
            "password2":         "AcademiaPass123!",
            "preferred_language": "tr",
            "zeitgeist_mode":    "classical",
        })
        assert resp.url == reverse("philosophers:list")

    def test_register_duplicate_email_fails(self, client, user):
        """Mevcut email ile kayıt başarısız olmalı."""
        url = reverse("accounts:register")
        resp = client.post(url, {
            "email":    user.email,
            "username": "duplicate",
            "password1": "DupPass123!",
            "password2": "DupPass123!",
        })
        assert resp.status_code == 200  # Form hataları sayfada
        assert User.objects.filter(username="duplicate").count() == 0

    def test_register_password_mismatch_fails(self, client):
        """Şifreler eşleşmeyince kayıt başarısız olmalı."""
        url = reverse("accounts:register")
        resp = client.post(url, {
            "email":    "mismatch@agora.ai",
            "username": "mismatch",
            "password1": "Pass123!",
            "password2": "Different123!",
        })
        assert resp.status_code == 200
        assert not User.objects.filter(email="mismatch@agora.ai").exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestLoginView:
    """Giriş görünümü testleri."""

    def test_login_page_loads(self, client):
        url = reverse("accounts:login")
        resp = client.get(url)
        assert resp.status_code == 200

    def test_login_with_valid_credentials(self, client, user):
        url = reverse("accounts:login")
        resp = client.post(url, {
            "email":    user.email,
            "password": "TestPass123!",
        })
        assert resp.status_code == 302
        assert resp.url == reverse("philosophers:list")

    def test_login_with_invalid_password_fails(self, client, user):
        url = reverse("accounts:login")
        resp = client.post(url, {
            "email":    user.email,
            "password": "WrongPassword!",
        })
        assert resp.status_code == 200

    def test_authenticated_user_redirected_from_login(self, auth_client):
        url = reverse("accounts:login")
        resp = auth_client.get(url)
        assert resp.status_code == 302


@pytest.mark.integration
@pytest.mark.django_db
class TestProfileView:
    """Profil görünümü testleri."""

    def test_profile_requires_login(self, client):
        url = reverse("accounts:profile")
        resp = client.get(url)
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_profile_loads_for_auth_user(self, auth_client):
        url = reverse("accounts:profile")
        resp = auth_client.get(url)
        assert resp.status_code == 200

    def test_profile_update(self, auth_client, user):
        url = reverse("accounts:profile")
        resp = auth_client.post(url, {
            "username":          "updated_name",
            "preferred_language": "en",
            "zeitgeist_mode":    "modern",
        })
        assert resp.status_code == 302
        user.refresh_from_db()
        assert user.username == "updated_name"
        assert user.preferred_language == "en"
        assert user.zeitgeist_mode == "modern"

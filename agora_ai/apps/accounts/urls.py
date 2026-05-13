# PATH: apps/accounts/urls.py
"""
Agora AI — Hesap URL Yönlendirmeleri
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Ana sayfa (landing)
    path("", views.home_view, name="home"),

    # Kayıt ol
    path("register/", views.register_view, name="register"),

    # Giriş yap
    path("login/", views.login_view, name="login"),

    # Çıkış yap
    path("logout/", views.logout_view, name="logout"),

    # Profil sayfası
    path("profile/", views.profile_view, name="profile"),
]

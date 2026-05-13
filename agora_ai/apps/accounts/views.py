# PATH: apps/accounts/views.py
"""
Agora AI — Hesap Görünümleri (Views)
Doküman Bölüm 5.1 (Kullanıcı Kaydı ve Onboarding Akışı) referans alınmıştır.

Akış:
    KULLANICI → /register (POST) → create_user() → login() → /philosophers/
    KULLANICI → /login (POST)    → authenticate() → session → /philosophers/
    KULLANICI → /logout          → session temizle → /
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, ProfileUpdateForm, RegisterForm


@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    Yeni kullanıcı kayıt görünümü.
    Doküman Akış 5.1:
        BAŞARILI → create_user() → login() → redirect /philosophers/
        HATA     → Form hataları ile sayfayı yeniden render
    """
    # Oturum açık kullanıcıyı ana sayfaya yönlendir
    if request.user.is_authenticated:
        return redirect("philosophers:list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Doküman Akış 5.1: CustomUser.objects.create_user() çağrısı
            user = form.save()
            # Doküman Akış 5.1: Otomatik giriş (login(request, user))
            login(request, user)
            messages.success(
                request,
                f"Hoş geldiniz, {user.username}! Agora'ya katıldınız. "
                "Bir filozofla sohbet başlatmak için aşağıdan birini seçin.",
            )
            # Doküman Akış 5.1: Redirect → /philosophers/ (Agora ana sayfası)
            return redirect("philosophers:list")
        else:
            messages.error(
                request,
                "Kayıt bilgilerinde hata var. Lütfen formu kontrol edin.",
            )
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Kullanıcı giriş görünümü.
    Giriş kimliği email'dir (Doküman Bölüm 4.1.1 — USERNAME_FIELD = 'email').
    """
    if request.user.is_authenticated:
        return redirect("philosophers:list")

    # 'next' parametresi ile yönlendirme hedefi
    next_url = request.GET.get("next") or request.POST.get("next", "")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # "Beni hatırla" seçeneği — oturum süresi ayarı
            if not form.cleaned_data.get("remember_me"):
                # Tarayıcı kapanınca oturumu sonlandır
                request.session.set_expiry(0)
            else:
                # 2 hafta oturumu canlı tut
                request.session.set_expiry(1_209_600)

            messages.success(
                request,
                f"Tekrar hoş geldiniz, {user.username}!",
            )

            # Güvenli next yönlendirmesi (sadece iç URL'ler)
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect("philosophers:list")
        else:
            messages.error(
                request,
                "E-posta adresi veya şifre hatalı.",
            )
    else:
        form = LoginForm(request)

    return render(
        request,
        "accounts/login.html",
        {"form": form, "next": next_url},
    )


@require_http_methods(["POST", "GET"])
def logout_view(request):
    """
    Kullanıcı çıkış görünümü.
    GET ile de erişilebilir (navbar çıkış butonu için).
    """
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.info(request, f"Görüşmek üzere, {username}!")
    return redirect("accounts:login")


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """
    Kullanıcı profil sayfası.
    Doküman Bölüm 6/AŞAMA 2: @login_required ile korunmalı.
    Kullanıcı; kullanıcı adı, dil ve zeitgeist modunu güncelleyebilir.
    """
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil bilgileriniz güncellendi.")
            return redirect("accounts:profile")
        else:
            messages.error(request, "Güncelleme sırasında hata oluştu.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    # Kullanıcıya ait sohbet istatistikleri (özet)
    context = {
        "form": form,
        "conversation_count": request.user.conversationsession_set.filter(
            is_active=True
        ).count(),
        "symposium_count": request.user.symposiumsession_set.count(),
    }
    return render(request, "accounts/profile.html", context)


def home_view(request):
    """
    Agora AI giriş (landing) sayfası.
    Oturum açık kullanıcıyı filozoflar listesine yönlendir.
    """
    if request.user.is_authenticated:
        return redirect("philosophers:list")
    return render(request, "home.html")

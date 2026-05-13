# PATH: apps/philosophers/urls.py
"""
Agora AI — Filozoflar URL Yönlendirmeleri
"""

from django.urls import path

from . import views

app_name = "philosophers"

urlpatterns = [
    # Doküman Bölüm 6/AŞAMA 3: /philosophers/ → Filozof listesi
    path("", views.philosopher_list, name="list"),

    # Doküman Bölüm 6/AŞAMA 3: /philosophers/<slug>/ → Profil detayı
    path("<slug:slug>/", views.philosopher_detail, name="detail"),
]

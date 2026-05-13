# PATH: apps/glossary/urls.py
"""Agora AI — Kavram Sözlüğü URL Yönlendirmeleri"""

from django.urls import path

from . import views

app_name = "glossary"

urlpatterns = [
    path("", views.concept_list, name="list"),
    path("api/", views.concept_api, name="api"),
    path("<slug:slug>/", views.concept_detail, name="detail"),
]

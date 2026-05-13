# PATH: apps/symposium/urls.py
"""
Agora AI — Sempozyum URL Yönlendirmeleri
Doküman Bölüm 5.4 endpoint'leri.
"""

# PATH: apps/symposium/urls.py
from django.urls import path
from . import views

app_name = "symposium"

urlpatterns = [
    path("",                            views.symposium_list,      name="list"),
    path("new/",                        views.create_symposium,    name="create"),
    path("<int:session_id>/",           views.symposium_chat,      name="chat"),
    path("<int:session_id>/detail/",    views.symposium_detail,    name="detail"),
    path("<int:session_id>/sse/turn/",  views.sse_philosopher_turn, name="sse_turn"),
    path("<int:session_id>/intervene/", views.user_intervene,      name="intervene"),
    path("<int:session_id>/sse/summary/", views.sse_summary,       name="sse_summary"),
]
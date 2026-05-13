# PATH: apps/conversations/urls.py
"""
Agora AI — Sohbet URL Yönlendirmeleri
Doküman Bölüm 5.2 ve 5.3 endpoint'leri.
"""

from django.urls import path

from . import views

app_name = "conversations"

urlpatterns = [
    # Sohbet listesi
    path("", views.conversation_list, name="list"),

    # Yeni sohbet (filozofun slug'ı ile)
    path("new/<slug:philosopher_slug>/", views.new_conversation, name="new"),

    # Sohbet arayüzü
    path("<int:session_id>/", views.chat_view, name="chat"),

    # Mesaj gönder (AJAX POST)
    path("<int:session_id>/send/", views.send_message, name="send"),

    # SSE streaming yanıt (Doküman Bölüm 5.3)
    path(
        "<int:session_id>/stream/<int:message_id>/",
        views.stream_response,
        name="stream",
    ),

    # Sohbet sil
    path("<int:session_id>/delete/", views.delete_conversation, name="delete"),
]

# PATH: tests/test_conversations.py
"""
Agora AI — Sohbet Motoru Testleri
Doküman Bölüm 6/AŞAMA 7: PromptBuilder, views ve model testleri.
Gemini API çağrıları mock ile izole edilir.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from django.urls import reverse

from apps.conversations.models import ConversationSession, Message
from apps.conversations.services.prompt_builder import (
    PromptBuilder,
    ZEITGEIST_CLASSICAL_BLOCK,
    ZEITGEIST_MODERN_BLOCK,
)


# ── Model Testleri ────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestConversationSessionModel:

    def test_str_representation(self, conversation_session):
        s = str(conversation_session)
        assert conversation_session.user.username in s
        assert conversation_session.philosopher.name in s

    def test_get_recent_messages_returns_correct_count(
        self, conversation_session
    ):
        for i in range(15):
            Message.objects.create(
                session=conversation_session,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Mesaj {i}",
            )
        recent = conversation_session.get_recent_messages(count=10)
        assert len(recent) == 10

    def test_get_recent_messages_chronological_order(
        self, conversation_session, user_message, assistant_message
    ):
        recent = conversation_session.get_recent_messages()
        if len(recent) >= 2:
            assert recent[0].created_at <= recent[1].created_at

    def test_last_message_property(
        self, conversation_session, user_message, assistant_message
    ):
        last = conversation_session.last_message
        assert last is not None
        assert last.pk == assistant_message.pk

    def test_get_message_count(
        self, conversation_session, user_message, assistant_message
    ):
        assert conversation_session.get_message_count() == 2


@pytest.mark.unit
@pytest.mark.django_db
class TestMessageModel:

    def test_is_user_message_property(self, user_message):
        assert user_message.is_user_message is True
        assert user_message.is_assistant_message is False

    def test_is_assistant_message_property(self, assistant_message):
        assert assistant_message.is_assistant_message is True
        assert assistant_message.is_user_message is False

    def test_str_representation(self, user_message):
        s = str(user_message)
        assert "USER" in s

    def test_rag_chunks_stored(self, assistant_message):
        assert isinstance(assistant_message.rag_chunks_used, list)
        assert len(assistant_message.rag_chunks_used) == 2


# ── PromptBuilder Testleri ────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestPromptBuilder:

    def test_classical_zeitgeist_block_in_prompt(
        self, philosopher, conversation_session
    ):
        conversation_session.zeitgeist_mode = "classical"
        conversation_session.save()
        builder = PromptBuilder(philosopher, conversation_session)
        prompt = builder.build_system_prompt(
            user_query="Test sorusu", rag_chunks=[]
        )
        assert "KLASİK" in prompt

    def test_modern_zeitgeist_block_in_prompt(
        self, philosopher, conversation_session
    ):
        conversation_session.zeitgeist_mode = "modern"
        conversation_session.save()
        builder = PromptBuilder(philosopher, conversation_session)
        prompt = builder.build_system_prompt(
            user_query="Test sorusu", rag_chunks=[]
        )
        assert "MODERN" in prompt

    def test_rag_chunks_included_in_prompt(
        self, philosopher, conversation_session
    ):
        builder = PromptBuilder(philosopher, conversation_session)
        chunks = ["Sokrates şöyle dedi...", "Platon yanıt verdi..."]
        prompt = builder.build_system_prompt(
            user_query="Test", rag_chunks=chunks
        )
        assert "Sokrates şöyle dedi" in prompt

    def test_no_rag_chunks_fallback_message(
        self, philosopher, conversation_session
    ):
        builder = PromptBuilder(philosopher, conversation_session)
        prompt = builder.build_system_prompt(
            user_query="Test", rag_chunks=[]
        )
        assert "kaynak metin bulunamadı" in prompt.lower()

    def test_context_summary_included(
        self, philosopher, conversation_session
    ):
        conversation_session.context_summary = "Önceki tartışma özetlendi."
        conversation_session.save()
        builder = PromptBuilder(philosopher, conversation_session)
        prompt = builder.build_system_prompt(
            user_query="Test", rag_chunks=[]
        )
        assert "Önceki tartışma özetlendi" in prompt

    def test_build_message_history_format(
        self, philosopher, conversation_session,
        user_message, assistant_message
    ):
        builder = PromptBuilder(philosopher, conversation_session)
        recent = conversation_session.get_recent_messages()
        history = builder.build_message_history(recent)
        assert isinstance(history, list)
        for item in history:
            assert "role" in item
            assert item["role"] in ("user", "model")
            assert "parts" in item

    def test_max_rag_chunks_limited_to_5(
        self, philosopher, conversation_session
    ):
        builder = PromptBuilder(philosopher, conversation_session)
        many_chunks = [f"Chunk {i}" for i in range(10)]
        prompt = builder.build_system_prompt(
            user_query="Test", rag_chunks=many_chunks
        )
        # Yalnızca ilk 5 chunk dahil edilmeli
        assert "Chunk 4" in prompt
        assert "Chunk 5" not in prompt


# ── View Testleri ─────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestConversationListView:

    def test_list_requires_login(self, client):
        url = reverse("conversations:list")
        resp = client.get(url)
        assert resp.status_code == 302

    def test_list_shows_user_sessions(
        self, auth_client, conversation_session
    ):
        url = reverse("conversations:list")
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert conversation_session.title.encode() in resp.content

    def test_list_does_not_show_other_users_sessions(
        self, auth_client, db, philosopher
    ):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.create_user(
            email="other@agora.ai",
            username="other",
            password="OtherPass123!",
        )
        ConversationSession.objects.create(
            user=other,
            philosopher=philosopher,
            title="Diğer kullanıcının sohbeti",
        )
        url = reverse("conversations:list")
        resp = auth_client.get(url)
        assert "Diğer kullanıcının".encode() not in resp.content


@pytest.mark.integration
@pytest.mark.django_db
class TestNewConversationView:

    def test_new_conversation_creates_session(
        self, auth_client, philosopher
    ):
        url = reverse("conversations:new", kwargs={"philosopher_slug": philosopher.slug})
        resp = auth_client.get(url)
        assert resp.status_code == 302
        assert ConversationSession.objects.filter(
            philosopher=philosopher
        ).exists()

    def test_new_conversation_copies_zeitgeist_from_user(
        self, auth_client, user, philosopher
    ):
        user.zeitgeist_mode = "modern"
        user.save()
        url = reverse("conversations:new", kwargs={"philosopher_slug": philosopher.slug})
        auth_client.get(url)
        session = ConversationSession.objects.filter(
            philosopher=philosopher
        ).latest("created_at")
        assert session.zeitgeist_mode == "modern"


@pytest.mark.integration
@pytest.mark.django_db
class TestChatView:

    def test_chat_requires_login(self, client, conversation_session):
        url = reverse("conversations:chat", kwargs={"session_id": conversation_session.pk})
        resp = client.get(url)
        assert resp.status_code == 302

    def test_chat_loads_for_owner(self, auth_client, conversation_session):
        url = reverse("conversations:chat", kwargs={"session_id": conversation_session.pk})
        resp = auth_client.get(url)
        assert resp.status_code == 200

    def test_chat_403_for_non_owner(self, client, db, philosopher):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.create_user(
            email="other2@agora.ai", username="other2", password="OtherPass123!"
        )
        session = ConversationSession.objects.create(
            user=other, philosopher=philosopher, title="Other"
        )
        client.login(username="test@agora.ai", password="TestPass123!")
        url = reverse("conversations:chat", kwargs={"session_id": session.pk})
        resp = client.get(url)
        assert resp.status_code in (302, 404)


@pytest.mark.integration
@pytest.mark.django_db
class TestSendMessageView:

    def test_send_message_creates_message(
        self, auth_client, conversation_session
    ):
        url = reverse("conversations:send", kwargs={"session_id": conversation_session.pk})
        resp = auth_client.post(
            url,
            data=json.dumps({"message": "Eudaimonia nedir?"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert "stream_url" in data
        assert Message.objects.filter(
            session=conversation_session, role="user"
        ).exists()

    def test_send_empty_message_returns_error(
        self, auth_client, conversation_session
    ):
        url = reverse("conversations:send", kwargs={"session_id": conversation_session.pk})
        resp = auth_client.post(
            url,
            data=json.dumps({"message": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_send_too_long_message_returns_error(
        self, auth_client, conversation_session
    ):
        url = reverse("conversations:send", kwargs={"session_id": conversation_session.pk})
        resp = auth_client.post(
            url,
            data=json.dumps({"message": "A" * 4001}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_send_requires_login(self, client, conversation_session):
        url = reverse("conversations:send", kwargs={"session_id": conversation_session.pk})
        resp = client.post(
            url,
            data=json.dumps({"message": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 302


@pytest.mark.integration
@pytest.mark.django_db
class TestDeleteConversationView:

    def test_delete_sets_inactive(self, auth_client, conversation_session):
        url = reverse("conversations:delete", kwargs={"session_id": conversation_session.pk})
        resp = auth_client.post(url)
        assert resp.status_code == 200
        conversation_session.refresh_from_db()
        assert conversation_session.is_active is False

# PATH: tests/conftest.py
"""
Agora AI — pytest Fixtures (conftest.py)
Doküman Bölüm 6/AŞAMA 7: Test altyapısı kurulumu.
Tüm testlerde kullanılan ortak fixture'lar burada tanımlanır.
"""

import pytest
from django.contrib.auth import get_user_model


User = get_user_model()


# ── Kullanıcı Fixture'ları ────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    """Standart test kullanıcısı."""
    return User.objects.create_user(
        email="test@agora.ai",
        username="testuser",
        password="TestPass123!",
        preferred_language="tr",
        zeitgeist_mode="classical",
    )


@pytest.fixture
def staff_user(db):
    """Admin yetkili test kullanıcısı."""
    return User.objects.create_user(
        email="staff@agora.ai",
        username="staffuser",
        password="StaffPass123!",
        is_staff=True,
    )


@pytest.fixture
def auth_client(client, user):
    """Oturum açmış test client'ı."""
    client.login(username=user.email, password="TestPass123!")
    return client


@pytest.fixture
def staff_client(client, staff_user):
    """Personel kullanıcıyla oturum açmış test client'ı."""
    client.login(username=staff_user.email, password="StaffPass123!")
    return client


# ── Filozof Fixture'ları ──────────────────────────────────────────────────────

@pytest.fixture
def philosopher(db):
    """Temel test filozofu."""
    from apps.philosophers.models import Philosopher
    return Philosopher.objects.create(
        name="Test Filozofu",
        slug="test-filozofu",
        era="Test Çağı, MÖ 100–50",
        school="Test Okulu",
        short_bio="Test amaçlı oluşturulmuş filozoftur.",
        system_prompt_template=(
            "Sen {philosopher_name}'sun. {era} döneminde yaşadın.\n"
            "{zeitgeist_block}\n"
            "Kaynaklar: {rag_context}\n"
            "Özet: {context_summary}"
        ),
        core_concepts=["Test Kavramı", "Deneme"],
        signature_style="Test üslubu.",
        is_active=True,
        display_order=99,
    )


@pytest.fixture
def philosophical_work(db, philosopher):
    """Tamamlanmış (completed) durumunda test eseri."""
    from apps.philosophers.models import PhilosophicalWork
    return PhilosophicalWork.objects.create(
        philosopher=philosopher,
        title="Test Eseri",
        ingestion_status=PhilosophicalWork.STATUS_COMPLETED,
        chunk_count=10,
    )


# ── Sohbet Fixture'ları ───────────────────────────────────────────────────────

@pytest.fixture
def conversation_session(db, user, philosopher):
    """Test sohbet oturumu."""
    from apps.conversations.models import ConversationSession
    return ConversationSession.objects.create(
        user=user,
        philosopher=philosopher,
        title="Test Sohbeti",
        zeitgeist_mode="classical",
    )


@pytest.fixture
def user_message(db, conversation_session):
    """Test kullanıcı mesajı."""
    from apps.conversations.models import Message
    return Message.objects.create(
        session=conversation_session,
        role="user",
        content="Eudaimonia nedir?",
    )


@pytest.fixture
def assistant_message(db, conversation_session):
    """Test asistan mesajı."""
    from apps.conversations.models import Message
    return Message.objects.create(
        session=conversation_session,
        role="assistant",
        content="Eudaimonia, mutluluk ve iyi yaşamdır.",
        rag_chunks_used=["test chunk 1", "test chunk 2"],
    )

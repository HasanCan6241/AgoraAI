# PATH: tests/test_symposium.py
"""
Agora AI — Sempozyum Testleri
Doküman Bölüm 6/AŞAMA 7: symposium app model ve view testleri.
"""

import pytest
from django.urls import reverse

from apps.symposium.models import SymposiumSession, SymposiumTurn


@pytest.mark.unit
@pytest.mark.django_db
class TestSymposiumSessionModel:

    def test_str_representation(self, db, user, philosopher):
        session = SymposiumSession.objects.create(
            user=user,
            topic="Özgür irade var mıdır?",
        )
        session.philosophers.add(philosopher)
        s = str(session)
        assert "Sempozyum" in s
        assert "Özgür irade" in s

    def test_default_status_is_pending(self, db, user):
        session = SymposiumSession.objects.create(
            user=user,
            topic="Test konusu",
        )
        assert session.status == SymposiumSession.STATUS_PENDING

    def test_is_complete_false_for_pending(self, db, user):
        session = SymposiumSession.objects.create(
            user=user, topic="Test"
        )
        assert session.is_complete is False

    def test_is_complete_true_for_completed(self, db, user):
        session = SymposiumSession.objects.create(
            user=user, topic="Test",
            status=SymposiumSession.STATUS_COMPLETED,
        )
        assert session.is_complete is True

    def test_philosopher_list_property(self, db, user, philosopher):
        session = SymposiumSession.objects.create(user=user, topic="Test")
        session.philosophers.add(philosopher)
        assert philosopher in session.philosopher_list


@pytest.mark.integration
@pytest.mark.django_db
class TestCreateSymposiumView:

    def test_create_requires_login(self, client):
        url = reverse("symposium:create")
        resp = client.get(url)
        assert resp.status_code == 302

    def test_create_page_loads(self, auth_client):
        url = reverse("symposium:create")
        resp = auth_client.get(url)
        assert resp.status_code == 200

    def test_create_with_valid_data(self, auth_client, db, philosopher):
        from apps.philosophers.models import Philosopher
        p2 = Philosopher.objects.create(
            name="İkinci Filozof",
            slug="ikinci-filozof",
            era="Test",
            short_bio="Test",
            system_prompt_template="Test {philosopher_name}",
            is_active=True,
        )
        url = reverse("symposium:create")
        resp = auth_client.post(url, {
            "topic":          "Mutluluk nedir?",
            "philosophers":   [philosopher.pk, p2.pk],
            "zeitgeist_mode": "classical",
            "rounds_count":   "2",
        })
        assert resp.status_code == 302
        assert SymposiumSession.objects.filter(topic="Mutluluk nedir?").exists()

    def test_create_with_one_philosopher_fails(
        self, auth_client, philosopher
    ):
        url = reverse("symposium:create")
        resp = auth_client.post(url, {
            "topic":        "Tek kişilik tartışma",
            "philosophers": [philosopher.pk],
            "rounds_count": "1",
        })
        assert resp.status_code == 200  # Form hatasıyla sayfada kalır
        assert not SymposiumSession.objects.filter(
            topic="Tek kişilik tartışma"
        ).exists()

    def test_create_with_empty_topic_fails(self, auth_client, philosopher):
        url = reverse("symposium:create")
        resp = auth_client.post(url, {
            "topic":        "",
            "philosophers": [philosopher.pk],
            "rounds_count": "1",
        })
        assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestSymposiumListView:

    def test_list_requires_login(self, client):
        url = reverse("symposium:list")
        resp = client.get(url)
        assert resp.status_code == 302

    def test_list_shows_user_sessions(self, auth_client, db, user):
        session = SymposiumSession.objects.create(
            user=user, topic="Listeleme testi"
        )
        url = reverse("symposium:list")
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert b"Listeleme testi" in resp.content

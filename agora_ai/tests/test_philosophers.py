# PATH: tests/test_philosophers.py
"""
Agora AI — Filozoflar App Testleri
Doküman Bölüm 6/AŞAMA 7: philosophers app birim ve entegrasyon testleri.
"""

import pytest
from django.urls import reverse

from apps.philosophers.models import Philosopher, PhilosophicalWork


# ── Model Testleri ────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestPhilosopherModel:

    def test_str_representation(self, philosopher):
        assert philosopher.name in str(philosopher)
        assert philosopher.era in str(philosopher)

    def test_get_absolute_url(self, philosopher):
        url = philosopher.get_absolute_url()
        assert philosopher.slug in url

    def test_get_core_concepts_list_returns_list(self, philosopher):
        result = philosopher.get_core_concepts_list()
        assert isinstance(result, list)
        assert "Test Kavramı" in result

    def test_get_core_concepts_list_empty(self, db):
        p = Philosopher.objects.create(
            name="Boş Filozof",
            slug="bos-filozof",
            era="Test",
            short_bio="Test",
            system_prompt_template="Test {philosopher_name}",
            core_concepts=[],
        )
        assert p.get_core_concepts_list() == []

    def test_work_count_counts_only_completed(self, philosopher):
        PhilosophicalWork.objects.create(
            philosopher=philosopher,
            title="Tamamlandı",
            ingestion_status=PhilosophicalWork.STATUS_COMPLETED,
            chunk_count=5,
        )
        PhilosophicalWork.objects.create(
            philosopher=philosopher,
            title="Bekliyor",
            ingestion_status=PhilosophicalWork.STATUS_PENDING,
        )
        assert philosopher.work_count == 1

    def test_inactive_philosopher_not_in_active_queryset(self, db):
        p = Philosopher.objects.create(
            name="Pasif Filozof",
            slug="pasif-filozof",
            era="Test",
            short_bio="Test",
            system_prompt_template="Test",
            is_active=False,
        )
        assert not Philosopher.objects.filter(slug="pasif-filozof", is_active=True).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestPhilosophicalWorkModel:

    def test_str_representation(self, philosophical_work):
        s = str(philosophical_work)
        assert philosophical_work.title in s
        assert philosophical_work.philosopher.name in s

    def test_is_ready_property_true_for_completed(self, philosophical_work):
        assert philosophical_work.is_ready is True

    def test_is_ready_property_false_for_pending(self, philosopher):
        work = PhilosophicalWork.objects.create(
            philosopher=philosopher,
            title="Bekleyen Eser",
            ingestion_status=PhilosophicalWork.STATUS_PENDING,
        )
        assert work.is_ready is False

    def test_status_transitions(self, philosopher):
        work = PhilosophicalWork.objects.create(
            philosopher=philosopher,
            title="Geçiş Testi",
            ingestion_status=PhilosophicalWork.STATUS_PENDING,
        )
        assert work.ingestion_status == "pending"
        work.ingestion_status = PhilosophicalWork.STATUS_PROCESSING
        work.save(update_fields=["ingestion_status"])
        work.refresh_from_db()
        assert work.ingestion_status == "processing"


# ── View Testleri ─────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestPhilosopherListView:

    def test_list_requires_login(self, client):
        url = reverse("philosophers:list")
        resp = client.get(url)
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_list_loads_for_authenticated(self, auth_client, philosopher):
        url = reverse("philosophers:list")
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert philosopher.name.encode() in resp.content

    def test_inactive_philosopher_not_listed(self, auth_client, db):
        p = Philosopher.objects.create(
            name="Gizli Filozof",
            slug="gizli-filozof",
            era="Test",
            short_bio="Test",
            system_prompt_template="Test",
            is_active=False,
        )
        url = reverse("philosophers:list")
        resp = auth_client.get(url)
        assert b"Gizli Filozof" not in resp.content

    def test_era_filter_works(self, auth_client, philosopher):
        url = reverse("philosophers:list") + f"?era={philosopher.era}"
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert philosopher.name.encode() in resp.content


@pytest.mark.integration
@pytest.mark.django_db
class TestPhilosopherDetailView:

    def test_detail_loads(self, auth_client, philosopher):
        url = reverse("philosophers:detail", kwargs={"slug": philosopher.slug})
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert philosopher.name.encode() in resp.content

    def test_detail_404_for_inactive(self, auth_client, db):
        p = Philosopher.objects.create(
            name="Pasif",
            slug="pasif-detail",
            era="Test",
            short_bio="Test",
            system_prompt_template="Test",
            is_active=False,
        )
        url = reverse("philosophers:detail", kwargs={"slug": p.slug})
        resp = auth_client.get(url)
        assert resp.status_code == 404

    def test_detail_404_for_nonexistent(self, auth_client):
        url = reverse("philosophers:detail", kwargs={"slug": "olmayan-filozof"})
        resp = auth_client.get(url)
        assert resp.status_code == 404

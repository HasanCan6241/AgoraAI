# PATH: apps/glossary/views.py
"""
Agora AI — Kavram Sözlüğü Görünümleri
Doküman Bölüm 6/AŞAMA 6: Felsefi kavramlar listesi, detay, arama API.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import PhilosophicalConcept

logger = logging.getLogger("agora.glossary")


@login_required
@require_http_methods(["GET"])
def concept_list(request):
    """Tüm aktif kavramları listeler. Arama ve filtre destekler."""
    query = request.GET.get("q", "").strip()
    philosopher_slug = request.GET.get("philosopher", "").strip()

    concepts = PhilosophicalConcept.objects.filter(
        is_active=True
    ).prefetch_related("philosophers")

    if query:
        concepts = concepts.filter(name__icontains=query)
    if philosopher_slug:
        concepts = concepts.filter(philosophers__slug=philosopher_slug)

    # Alfabetik harf grupları
    letter_groups: dict = {}
    for concept in concepts:
        letter = concept.name[0].upper()
        letter_groups.setdefault(letter, []).append(concept)

    return render(
        request,
        "glossary/concept_list.html",
        {
            "letter_groups": sorted(letter_groups.items()),
            "query": query,
            "total_count": concepts.count(),
        },
    )


@login_required
@require_http_methods(["GET"])
def concept_detail(request, slug: str):
    """Tek bir kavramın detay sayfası."""
    concept = get_object_or_404(PhilosophicalConcept, slug=slug, is_active=True)
    related = concept.related_concepts.filter(is_active=True)
    return render(
        request,
        "glossary/concept_detail.html",
        {"concept": concept, "related": related},
    )


@login_required
@require_http_methods(["GET"])
def concept_api(request):
    """
    JSON arama API'si — sohbet arayüzünde kavram tooltip'i için kullanılır.
    GET /glossary/api/?q=eudaimonia
    Yanıt: [{"name", "short_definition", "slug"}, ...]
    """
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})

    concepts = (
        PhilosophicalConcept.objects.filter(
            is_active=True,
            name__icontains=query,
        )
        .values("name", "original_term", "short_definition", "slug")[:8]
    )

    return JsonResponse({"results": list(concepts)})

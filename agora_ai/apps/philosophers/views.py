# PATH: apps/philosophers/views.py
"""
Agora AI — Filozof Görünümleri (Views)
Doküman Bölüm 6/AŞAMA 3:
    - /philosophers/         → Filozof listesi
    - /philosophers/<slug>/  → Filozof profil detayı
Tüm view'lar @login_required ile korunmuştur.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Philosopher


@login_required
@require_http_methods(["GET"])
def philosopher_list(request):
    """
    Aktif filozofları listeler.
    Doküman Bölüm 6/AŞAMA 3: /philosophers/ → philosopher_list.html
    Sıralama: display_order, ardından name (Philosopher.Meta.ordering).
    """
    philosophers = Philosopher.objects.filter(is_active=True).prefetch_related(
        "works"
    )

    # Filtre: dönem veya okul bazında
    era_filter = request.GET.get("era", "").strip()
    school_filter = request.GET.get("school", "").strip()

    if era_filter:
        philosophers = philosophers.filter(era__icontains=era_filter)
    if school_filter:
        philosophers = philosophers.filter(school__icontains=school_filter)

    # Tüm dönemleri filtre seçeneği için topla
    all_eras = (
        Philosopher.objects.filter(is_active=True)
        .values_list("era", flat=True)
        .distinct()
        .order_by("era")
    )

    context = {
        "philosophers": philosophers,
        "all_eras": all_eras,
        "era_filter": era_filter,
        "school_filter": school_filter,
        "philosopher_count": philosophers.count(),
    }
    return render(request, "philosophers/philosopher_list.html", context)


@login_required
@require_http_methods(["GET"])
def philosopher_detail(request, slug):
    """
    Tek bir filozofun profil sayfasını gösterir.
    Doküman Bölüm 6/AŞAMA 3: /philosophers/<slug>/ → philosopher_detail.html
    İçerik: biyografi, dönem, temel kavramlar, eserler listesi.
    """
    philosopher = get_object_or_404(Philosopher, slug=slug, is_active=True)

    # Tamamlanmış (RAG'a hazır) ve toplam eser sayısı
    works_ready = philosopher.works.filter(ingestion_status="completed")
    works_all = philosopher.works.all()

    # Bu kullanıcının bu filozofla kaç sohbeti var?
    session_count = request.user.conversationsession_set.filter(
        philosopher=philosopher, is_active=True
    ).count()

    context = {
        "philosopher": philosopher,
        "works_ready": works_ready,
        "works_all": works_all,
        "session_count": session_count,
        "core_concepts": philosopher.get_core_concepts_list(),
    }
    return render(request, "philosophers/philosopher_detail.html", context)

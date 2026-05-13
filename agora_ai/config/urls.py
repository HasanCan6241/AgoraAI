# PATH: config/urls.py
"""
Agora AI — Ana URL Yönlendirici
Doküman Bölüm 3.2: config/urls.py — Ana URL router
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin paneli
    path("admin/", admin.site.urls),
    path("admin/doc/", include("django.contrib.admindocs.urls")),

    # Kullanıcı yönetimi (Doküman Bölüm 3.2 — apps/accounts)
    path("accounts/", include("apps.accounts.urls")),

    # Filozof profilleri (Doküman Bölüm 3.2 — apps/philosophers)
    path("philosophers/", include("apps.philosophers.urls")),

    # Sohbet motoru (Doküman Bölüm 3.2 — apps/conversations)
    path("conversations/", include("apps.conversations.urls")),

    # Sempozyum modu (Doküman Bölüm 3.2 — apps/symposium)
    path("symposium/", include("apps.symposium.urls")),

    # Kavram sözlüğü API (Doküman Bölüm 3.2 — apps/glossary)
    path("glossary/", include("apps.glossary.urls")),

    # RAG ingestion API (Doküman Bölüm 4.2 — apps/rag)
    path("rag/", include("apps.rag.urls")),

    # Ana sayfa (accounts login redirect'i olmayan ziyaretçiler için)
    path("", include("apps.accounts.urls")),
]

# Geliştirme ortamında statik ve medya dosyalarını sun
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )

    # Django Debug Toolbar (kurulu ise)
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns = [
            path("__debug__/", include("debug_toolbar.urls")),
        ] + urlpatterns
    except ImportError:
        pass

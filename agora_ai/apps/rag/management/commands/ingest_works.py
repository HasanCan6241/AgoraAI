# PATH: apps/rag/management/commands/ingest_works.py
"""
Agora AI — Management Command: ingest_works
Doküman Bölüm 6/AŞAMA 7: Tüm pending/failed eserleri Celery'ye gönder.

Kullanım:
    python manage.py ingest_works
    python manage.py ingest_works --philosopher sokrates
    python manage.py ingest_works --force          # completed olanları da yeniden işle
    python manage.py ingest_works --sync           # Celery olmadan senkron çalıştır
"""

import logging

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger("agora.management")


class Command(BaseCommand):
    help = "Felsefi eserleri RAG pipeline'ına gönderir (Celery veya senkron)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--philosopher",
            type=str,
            default=None,
            help="Yalnızca bu slug'a sahip filozofun eserlerini işle.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="'completed' durumdaki eserleri de yeniden işle.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            default=False,
            help="Celery kullanmadan senkron olarak işle (geliştirme/test için).",
        )
        parser.add_argument(
            "--work-id",
            type=int,
            default=None,
            help="Yalnızca belirtilen ID'li eseri işle.",
        )

    def handle(self, *args, **options):
        from apps.philosophers.models import PhilosophicalWork

        # ── Hedef eserleri belirle ────────────────────────────────────
        queryset = PhilosophicalWork.objects.select_related(
            "philosopher"
        ).exclude(original_file="")

        if options["work_id"]:
            queryset = queryset.filter(pk=options["work_id"])
        elif options["philosopher"]:
            queryset = queryset.filter(
                philosopher__slug=options["philosopher"]
            )

        if not options["force"]:
            queryset = queryset.exclude(
                ingestion_status=PhilosophicalWork.STATUS_COMPLETED
            )

        if not queryset.exists():
            self.stdout.write(
                self.style.WARNING("İşlenecek eser bulunamadı.")
            )
            return

        total = queryset.count()
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"{total} eser {'senkron' if options['sync'] else 'Celery'} "
                "ile işlenecek..."
            )
        )

        success = 0
        failed = 0

        for work in queryset:
            label = f"  [{work.philosopher.name}] {work.title}"

            if options["sync"]:
                # ── Senkron mod (test / geliştirme) ──────────────────
                from apps.rag.services.ingestion_pipeline import run_ingestion
                ok, msg = run_ingestion(work_id=work.pk)
                if ok:
                    self.stdout.write(self.style.SUCCESS(f"✅ {label}"))
                    success += 1
                else:
                    self.stdout.write(self.style.ERROR(f"❌ {label}: {msg}"))
                    failed += 1
            else:
                # ── Celery modu ───────────────────────────────────────
                try:
                    from apps.rag.tasks import ingest_philosophical_work
                    work.ingestion_status = PhilosophicalWork.STATUS_PENDING
                    work.ingestion_error = ""
                    work.save(
                        update_fields=["ingestion_status", "ingestion_error"]
                    )
                    ingest_philosophical_work.delay(work.pk)
                    self.stdout.write(
                        self.style.SUCCESS(f"📤 {label} → kuyruğa alındı")
                    )
                    success += 1
                except Exception as exc:
                    self.stdout.write(
                        self.style.ERROR(f"❌ {label}: {exc}")
                    )
                    failed += 1

        # ── Özet ─────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Tamamlandı: {success} başarılı, {failed} hatalı")
        )
        if failed:
            raise CommandError(f"{failed} eser işlenemedi.")

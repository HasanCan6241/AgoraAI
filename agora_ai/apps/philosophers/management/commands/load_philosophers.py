# PATH: apps/philosophers/management/commands/load_philosophers.py
"""
Agora AI — Management Command: load_philosophers
Doküman Bölüm 6/AŞAMA 7: Başlangıç filozoflarını fixture'dan yükler.

Kullanım:
    python manage.py load_philosophers
    python manage.py load_philosophers --reset   # Mevcut filozofları sil ve yeniden yükle
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Başlangıç filozoflarını initial_philosophers.json fixture'ından yükler."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            default=False,
            help="Yükleme öncesi tüm mevcut filozofları sil (dikkatli kullan!).",
        )

    def handle(self, *args, **options):
        from apps.philosophers.models import Philosopher

        if options["reset"]:
            count = Philosopher.objects.count()
            Philosopher.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"{count} mevcut filozof silindi.")
            )

        # Django'nun built-in loaddata komutunu çağır
        from django.core.management import call_command

        try:
            call_command("loaddata", "initial_philosophers", verbosity=1)
            total = Philosopher.objects.count()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {total} filozof başarıyla yüklendi."
                )
            )
        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(f"❌ Fixture yükleme hatası: {exc}")
            )

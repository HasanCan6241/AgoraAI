#!/usr/bin/env python
# PATH: manage.py
"""
Agora AI — Django Yönetim Aracı.
Geliştirme ortamı için DJANGO_SETTINGS_MODULE development olarak ayarlandı.
"""

import os
import sys


def main():
    """Django yönetim görevlerini çalıştır."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "config.settings.development"
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django import edilemedi. Sanal ortamın aktif olduğundan ve "
            "Django'nun kurulu olduğundan emin olun."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

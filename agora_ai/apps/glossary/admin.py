# PATH: apps/glossary/admin.py
"""Agora AI — Kavram Sözlüğü Admin Paneli"""

from django.contrib import admin

from .models import PhilosophicalConcept


@admin.register(PhilosophicalConcept)
class PhilosophicalConceptAdmin(admin.ModelAdmin):
    list_display  = ["name", "original_term", "philosopher_names", "is_active", "created_at"]
    list_filter   = ["is_active", "philosophers"]
    search_fields = ["name", "original_term", "short_definition"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal   = ["philosophers", "related_concepts"]
    ordering = ["name"]

    def philosopher_names(self, obj):
        names = [p.name for p in obj.philosophers.all()]
        return ", ".join(names) if names else "—"

    philosopher_names.short_description = "Filozoflar"

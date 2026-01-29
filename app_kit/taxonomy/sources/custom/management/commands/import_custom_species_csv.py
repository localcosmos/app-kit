import csv
import os
from typing import Optional, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from taxonomy.models import TaxonomyModelRouter


class Command(BaseCommand):
    help = (
        'Importiert die Arten-/Taxa-CSV (|-getrennt). Erkennt Headerzeile automatisch und überspringt sie.\n'
        'Unterstütztes Layout (aktuell):\n'
        '  0: scientific_name | 1: rank | 2: parent_lat | 3: parent_code | 4: de | 5: en | 6: nl | 7: da'
    )

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Pfad zur Arten-CSV (|-getrennt).')
        parser.add_argument('--delimiter', type=str, default='|', help='Trennzeichen (Standard: |).')
        parser.add_argument('--encoding', type=str, default='utf-8', help='Datei-Kodierung (Standard: utf-8).')
        parser.add_argument('--dry-run', action='store_true', help='Nur prüfen, am Ende zurückrollen.')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        delimiter = options['delimiter'] or '|'
        encoding = options['encoding']
        dry_run = options['dry_run']

        if not os.path.exists(csv_path):
            raise CommandError(f'Datei nicht gefunden: {csv_path}')

        models = TaxonomyModelRouter('taxonomy.sources.custom')
        self.stdout.write(self.style.NOTICE('Quelle: taxonomy.sources.custom'))
        self.stdout.write(self.style.NOTICE(f'Trennzeichen: {repr(delimiter)}'))

        created = 0
        skipped = 0
        existing = 0
        rows = 0
        self._missing_parents = {}
        self._header_skipped = False
        self._existing_names = []

        with open(csv_path, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f, delimiter=delimiter)

            with transaction.atomic():
                for parts in reader:
                    rows += 1
                    if not parts:
                        continue
                    # Skip header line if present
                    if not self._header_skipped and self._looks_like_header(parts):
                        self._header_skipped = True
                        continue
                    c, e, s, existing_name = self._import_species_row(models, parts)
                    created += c
                    existing += e
                    skipped += s
                    if e and existing_name:
                        # preserve insertion order, avoid duplicates
                        if existing_name not in self._existing_names:
                            self._existing_names.append(existing_name)

                if dry_run:
                    # Rollback alle DB-Änderungen, aber dennoch Auswertung anzeigen
                    transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'Fertig. Erstellt: {created}, vorhanden: {existing}, übersprungen: {skipped}, Zeilen: {rows}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-Run: Alle Änderungen wurden zurückgerollt.'))

        if existing and self._existing_names:
            self.stdout.write(self.style.NOTICE('Bereits vorhandene Taxa (exakt):'))
            for nm in self._existing_names:
                self.stdout.write(f'- {nm}')

        if skipped and self._missing_parents:
            self.stdout.write(self.style.WARNING('Übersprungene Zeilen wegen fehlendem Eltern-Taxon (Auszug):'))
            # Zeige bis zu 25 fehlende Eltern mit Häufigkeit
            shown = 0
            for parent_name, count in sorted(self._missing_parents.items(), key=lambda x: -x[1]):
                self.stdout.write(f'- {parent_name or "<leer>"}: {count}')
                shown += 1
                if shown >= 25:
                    break

    def _looks_like_header(self, parts: List[str]) -> bool:
        if not parts:
            return False
        p0 = (parts[0] or '').strip().lower()
        p1 = (parts[1] or '').strip().lower() if len(parts) > 1 else ''
        # Typical header tokens
        header_tokens = {'scientific name', 'name', 'latname', 'parent taxon', 'rank', 'de', 'en', 'nl', 'dk'}
        return (p0 in header_tokens) or (p1 in header_tokens)

    def _get_parent(self, models, parent_latname: str):
        if not parent_latname:
            return None
        # exakter Treffer zuerst
        parent = models.TaxonTreeModel.objects.filter(taxon_latname=parent_latname).first()
        if parent:
            return parent
        # Fallback: case-insensitive Vergleich
        return models.TaxonTreeModel.objects.filter(taxon_latname__iexact=parent_latname).first()

    def _get_or_create_taxon(self, models, parent, latname: str, rank: str):
        if not latname:
            return None, False

        r = (rank or 'species').strip().lower()
        qs = models.TaxonTreeModel.objects.filter(taxon_latname=latname, rank=r)
        if parent is None:
            qs = qs.filter(is_root_taxon=True)
        else:
            qs = qs.filter(parent=parent)

        instance = qs.first()
        created = False
        if not instance:
            extra = {'rank': r}
            if parent is None:
                extra['is_root_taxon'] = True
            else:
                extra['parent'] = parent
            instance = models.TaxonTreeModel.objects.create(latname, None, **extra)
            created = True
        return instance, created

    def _add_locale_if_present(self, models, taxon, name: Optional[str], language: str):
        if not taxon or not name:
            return False
        exists = models.TaxonLocaleModel.objects.filter(taxon=taxon, name=name, language=language).exists()
        if not exists:
            models.TaxonLocaleModel.objects.create(taxon, name, language, preferred=True)
            return True
        return False

    def _import_species_row(self, models, parts: List[str]):
        # Unterstütztes Layout (aktuell):
        # 0: scientific_name | 1: rank | 2: parent_lat | 3: parent_code | 4: de | 5: en | 6: nl | 7: da

        # Normalize parts
        parts = [(p or '').strip() for p in parts]

        # Minimalprüfung: mindestens 4 Spalten (bis parent_code) erwartet
        if len(parts) < 4:
            return 0, 0, 1, None

        name = parts[0]
        rank = (parts[1] or 'species').strip().lower()
        parent_latname = parts[2]
        # parent_code aktuell informativ, optional verwendbar
        # parent_code = parts[3]
        locale_start_idx = 4

        parent = self._get_parent(models, parent_latname) if parent_latname else None
        # If no parent and this should be a root-level taxon, allow creation with no parent
        if not parent and parent_latname:
            key = parent_latname
            self._missing_parents[key] = self._missing_parents.get(key, 0) + 1
            return 0, 0, 1, None

        taxon, created = self._get_or_create_taxon(models, parent, name, rank)
        if not taxon:
            return 0, 0, 1, None

        # Attach vernacular locales if present (de, en, nl, da)
        locale_langs = ['de', 'en', 'nl', 'da']
        for offset, lang in enumerate(locale_langs):
            idx = locale_start_idx + offset
            val = parts[idx] if idx < len(parts) else ''
            self._add_locale_if_present(models, taxon, val, lang)

        return (1, 0, 0, None) if created else (0, 1, 0, name)

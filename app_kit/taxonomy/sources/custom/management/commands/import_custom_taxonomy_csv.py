# temporary script for a one-time import of BeachExplorer's higher taxonom
import csv
import os
import re
from typing import List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from taxonomy.models import TaxonomyModelRouter

RANK_SET = set([
    'domain','kingdom','phylum','division','class','order','family','genus','species',
    'subkingdom','infrakingdom','superphylum','subphylum','infraphylum',
    'superclass','subclass','infraclass','superorder','suborder',
    'infraorder','parvorder','superfamily','subfamily','tribe','subtribe',
    'clade'
])


def is_code_like(val: str) -> bool:
    return bool(re.fullmatch(r'[a-z]{2,6}', val))

def _non_empty_indices(parts: List[str]) -> List[int]:
    return [i for i, p in enumerate(parts) if p]


class Command(BaseCommand):
    help = 'Import a custom taxonomy tree from a GROK-Rang CSV (headerlos, |-getrennt).'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Pfad zur GROK-Rang CSV-Datei (ohne Header).')
        parser.add_argument('--language', type=str, default=None,
                            help='Sprachcode für Bezeichnungen aus dem Pfad (z. B. de, en).')
        parser.add_argument('--delimiter', type=str, default='|',
                            help='Trennzeichen (Standard: |).')
        parser.add_argument('--encoding', type=str, default='utf-8',
                            help='Datei-Kodierung (Standard: utf-8).')
        parser.add_argument('--dry-run', action='store_true', help='Nur prüfen, am Ende zurückrollen.')
        parser.add_argument('--report-limit', type=int, default=10,
                            help='Maximale Anzahl Beispiel-Einträge in der Dry-Run-Übersicht (Standard: 10).')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        language = options['language']
        delimiter = options['delimiter'] or '|'
        encoding = options['encoding']
        dry_run = options['dry_run']

        if not os.path.exists(csv_path):
            raise CommandError(f'Datei nicht gefunden: {csv_path}')

        models = TaxonomyModelRouter('taxonomy.sources.custom')
        self.stdout.write(self.style.NOTICE('Quelle: taxonomy.sources.custom'))
        self.stdout.write(self.style.NOTICE(f'Trennzeichen: {repr(delimiter)}'))

        # track last Latin parent per depth to build a Latin-only hierarchy
        self.depth_taxon = {}

        with open(csv_path, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f, delimiter=delimiter)
            created_count = 0
            existing_count = 0
            skipped_count = 0
            skip_reasons = {}
            skipped_examples = []
            row_index = 0

            try:
                with transaction.atomic():
                    for parts in reader:
                        row_index += 1
                        if not parts:
                            # Treat truly empty lines as skipped for reporting
                            skipped_count += 1
                            skip_reasons['empty line'] = skip_reasons.get('empty line', 0) + 1
                            if len(skipped_examples) < (options.get('report_limit') or 10):
                                skipped_examples.append({'row': row_index, 'reason': 'empty line', 'raw': []})
                            continue
                        c, e, s, reason = self._import_grok_row(models, parts, language)
                        created_count += c
                        existing_count += e
                        if s:
                            skipped_count += s
                            if reason:
                                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                                if len(skipped_examples) < (options.get('report_limit') or 10):
                                    skipped_examples.append({'row': row_index, 'reason': reason, 'raw': parts})

                    if dry_run:
                        # Print a detailed dry-run report before rolling back
                        self.stdout.write(self.style.WARNING('Dry-Run Bericht:'))
                        self.stdout.write(f'  Zeilen gelesen: {row_index}')
                        self.stdout.write(f'  Würde erstellen: {created_count}')
                        self.stdout.write(f'  Bereits vorhanden: {existing_count}')
                        self.stdout.write(f'  Übersprungen: {skipped_count}')
                        if skip_reasons:
                            self.stdout.write('  Gründe für Überspringen:')
                            for r, cnt in sorted(skip_reasons.items(), key=lambda x: (-x[1], x[0])):
                                self.stdout.write(f'    - {r}: {cnt}')
                        if skipped_examples:
                            self.stdout.write('  Beispiele übersprungener Einträge:')
                            for ex in skipped_examples:
                                preview = '|'.join([str(p) for p in ex.get('raw', [])])
                                self.stdout.write(f"    - Zeile {ex['row']}: {ex['reason']} -> {preview}")
                        # Trigger rollback
                        raise CommandError('Dry-Run abgeschlossen: Änderungen werden zurückgerollt.')

            except CommandError as e:
                if 'Dry-Run abgeschlossen' in str(e):
                    self.stdout.write(self.style.WARNING(str(e)))
                    return
                raise

        self.stdout.write(self.style.SUCCESS(
            f'Fertig. Erstellt: {created_count}, vorhanden: {existing_count}, Zeilen: {row_index}'))

    def _get_or_create(self, models, parent, latname, author, rank):
        existing_qs = models.TaxonTreeModel.objects.filter(taxon_latname=latname, rank=rank)
        if parent is None:
            existing_qs = existing_qs.filter(is_root_taxon=True)
        else:
            existing_qs = existing_qs.filter(parent=parent)

        instance = existing_qs.first()
        created = False
        if not instance:
            extra = {'rank': rank}
            if parent is None:
                extra['is_root_taxon'] = True
            else:
                extra['parent'] = parent
            instance = models.TaxonTreeModel.objects.create(latname, None, **extra)
            created = True
        return instance, created

    def _clear_deeper_depth(self, depth: int):
        # drop any cached parents deeper than current depth
        for d in list(self.depth_taxon.keys()):
            if d > depth:
                del self.depth_taxon[d]

    def _import_grok_row(self, models, parts: List[str], language: Optional[str]):
        # Normalize tokens but keep positional layout
        parts = [(p or '').strip() for p in parts]
        if not parts or len(parts) < 3:
            return 0, 0, 1, 'empty or too few columns'

        # Fixed GROK layout: [...path..., latin, code, rank]
        rank = parts[-1]
        if not rank:
            return 0, 0, 1, 'missing rank'
        latin = parts[-3] if len(parts) >= 3 else ''
        if not latin:
            return 0, 0, 1, 'missing latin name'

        # Path segments are all tokens before latin
        path_segments = [p for p in parts[:-3] if p]
        depth = len(path_segments)
        parent = self.depth_taxon.get(depth - 1) if depth > 0 else None

        taxon, created = self._get_or_create(models, parent, latin, author=None, rank=rank)

        # Store this taxon as the current parent at its depth and clear deeper cache
        self.depth_taxon[depth] = taxon
        self._clear_deeper_depth(depth)

        # Locale: letzter Pfadteil als Bezeichnung (attach vernacular to Latin taxon)
        if path_segments and language:
            vernacular = path_segments[-1]
            exists = models.TaxonLocaleModel.objects.filter(
                taxon=taxon, name=vernacular, language=language
            ).exists()
            if not exists:
                models.TaxonLocaleModel.objects.create(taxon, vernacular, language, preferred=True)

        return (1, 0, 0, None) if created else (0, 1, 0, None)

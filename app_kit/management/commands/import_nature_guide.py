"""
import_nature_guide management command
--------------------------------------
Imports a single Nature Guide exported by export_nature_guide into a target
tenant schema that already contains other nature guides.

Strategy
~~~~~~~~
Django fixtures use integer primary keys.  If the target schema already has
rows in the same tables the import will collide.  To avoid that, every model
in the fixture receives a PK offset equal to the current maximum PK in the
target table.  All foreign-key and M2M references inside the fixture are
updated with the same offsets before loaddata is called.

NatureGuidesTaxonTree stores the NatureGuide's integer PK encoded inside the
taxon_nuid / source_id strings.  Those strings are rewritten with the new
nature-guide PK after the PK offsets are computed.

Image files are extracted from the ZIP and placed under MEDIA_ROOT, with the
source schema name replaced by the target schema name in their paths.
"""

import os
import json
import zipfile
import tempfile
import shutil

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType
from django_tenants.utils import schema_context

from app_kit.features.nature_guides.models import (
    NatureGuide, MetaNode, NatureGuidesTaxonTree, NatureGuideCrosslinks,
    MatrixFilterSpace, NatureGuidesTaxonSynonym, NatureGuidesTaxonLocale,
    MatrixFilter, NodeFilterSpace, MatrixFilterRestriction,
)
from app_kit.models import ContentImage, ImageStore
from app_kit.taxonomy.utils import NuidManager

# Models that have a unique slug field needing deduplication before loaddata
SLUG_MODELS = {
    'nature_guides.natureguidestaxontree': NatureGuidesTaxonTree,
    'nature_guides.natureguidestaxonsynonym': NatureGuidesTaxonSynonym,
    'nature_guides.natureguidestaxonlocale': NatureGuidesTaxonLocale,
}


# ---------------------------------------------------------------------------
# FK and M2M relationships that need PK remapping.
# Each entry: (field_name_in_fixture, model_label_of_referenced_model)
# ---------------------------------------------------------------------------
FK_FIELDS = {
    'nature_guides.metanode': [
        ('nature_guide', 'nature_guides.natureguide'),
    ],
    'nature_guides.natureguidestaxontree': [
        ('nature_guide', 'nature_guides.natureguide'),
        ('meta_node', 'nature_guides.metanode'),
        # self-referential parent (None for root, so we guard against that)
        ('parent', 'nature_guides.natureguidestaxontree'),
    ],
    'nature_guides.natureguidecrosslinks': [
        ('parent', 'nature_guides.natureguidestaxontree'),
        ('child', 'nature_guides.natureguidestaxontree'),
    ],
    'nature_guides.matrixfilter': [
        ('meta_node', 'nature_guides.metanode'),
    ],
    'nature_guides.matrixfilterspace': [
        ('matrix_filter', 'nature_guides.matrixfilter'),
    ],
    'nature_guides.nodefilterspace': [
        ('node', 'nature_guides.natureguidestaxontree'),
        ('matrix_filter', 'nature_guides.matrixfilter'),
    ],
    'nature_guides.matrixfilterrestriction': [
        ('restricted_matrix_filter', 'nature_guides.matrixfilter'),
        ('restrictive_matrix_filter', 'nature_guides.matrixfilter'),
    ],
    # NatureGuidesTaxonSynonym/Locale FK uses name_uuid (UUID), not PK → skip
    'app_kit.contentimage': [
        ('image_store', 'app_kit.imagestore'),
    ],
}

M2M_FIELDS = {
    'nature_guides.nodefilterspace': [
        ('values', 'nature_guides.matrixfilterspace'),
    ],
    'nature_guides.matrixfilterrestriction': [
        ('values', 'nature_guides.matrixfilterspace'),
    ],
}

# ContentType natural-key tuple → model label used in FK_FIELDS / offsets
CONTENT_TYPE_MODEL_MAP = {
    ('app_kit', 'natureguide'): 'nature_guides.natureguide',
    ('nature_guides', 'natureguide'): 'nature_guides.natureguide',
    ('app_kit', 'metanode'): 'nature_guides.metanode',
    ('nature_guides', 'metanode'): 'nature_guides.metanode',
    ('app_kit', 'natureguidestaxontree'): 'nature_guides.natureguidestaxontree',
    ('nature_guides', 'natureguidestaxontree'): 'nature_guides.natureguidestaxontree',
    ('app_kit', 'matrixfilterspace'): 'nature_guides.matrixfilterspace',
    ('nature_guides', 'matrixfilterspace'): 'nature_guides.matrixfilterspace',
}

# All model classes we need max-PK queries for
MODEL_CLASSES = {
    'nature_guides.natureguide': NatureGuide,
    'nature_guides.metanode': MetaNode,
    'nature_guides.natureguidestaxontree': NatureGuidesTaxonTree,
    'nature_guides.natureguidecrosslinks': NatureGuideCrosslinks,
    'nature_guides.matrixfilter': MatrixFilter,
    'nature_guides.matrixfilterspace': MatrixFilterSpace,
    'nature_guides.nodefilterspace': NodeFilterSpace,
    'nature_guides.matrixfilterrestriction': MatrixFilterRestriction,
    'nature_guides.natureguidestaxonsynonym': NatureGuidesTaxonSynonym,
    'nature_guides.natureguidestaxonlocale': NatureGuidesTaxonLocale,
    'app_kit.imagestore': ImageStore,
    'app_kit.contentimage': ContentImage,
}


def _compute_offsets():
    """Return {model_label: max_existing_pk} for every model we export."""
    offsets = {}
    for label, ModelClass in MODEL_CLASSES.items():
        last = ModelClass.objects.order_by('-pk').first()
        offsets[label] = last.pk if last else 0
    return offsets


def _collect_existing_slugs():
    """Return {model_label: set_of_existing_slugs} for models with slug fields."""
    existing = {}
    for label, ModelClass in SLUG_MODELS.items():
        existing[label] = set(
            ModelClass.objects.values_list('slug', flat=True).exclude(slug__isnull=True)
        )
    return existing


def _deduplicate_slugs(data, existing_slugs):
    """
    Ensure no slug in the fixture collides with an already-existing slug in the
    target schema.  Conflicting slugs get a numeric suffix appended.
    """
    for obj in data:
        model = obj['model']
        if model not in SLUG_MODELS:
            continue
        slug = obj['fields'].get('slug')
        if not slug:
            continue
        taken = existing_slugs.setdefault(model, set())
        if slug in taken:
            counter = 2
            base = slug[:45]  # leave room for suffix within SlugField max_length=100
            new_slug = f'{base}-{counter}'
            while new_slug in taken:
                counter += 1
                new_slug = f'{base}-{counter}'
            obj['fields']['slug'] = new_slug
            slug = new_slug
        taken.add(slug)
    return data


def _remap_fixture(data, offsets, old_ng_nuid, new_ng_nuid, source_schema=None, target_schema=None):
    """
    Mutate the fixture list in-place:
    - shift every PK and FK by the appropriate offset
    - rewrite nuid prefixes in NatureGuidesTaxonTree records
    - rewrite nuid prefix occurrences inside MetaNode.children_cache JSON
    """
    for obj in data:
        model = obj['model']
        offset = offsets.get(model, 0)
        fields = obj['fields']

        # --- Own PK ---
        if offset > 0:
            obj['pk'] += offset

        # --- Regular FK fields ---
        for field_name, ref_model in FK_FIELDS.get(model, []):
            ref_offset = offsets.get(ref_model, 0)
            if ref_offset > 0 and fields.get(field_name) is not None:
                fields[field_name] += ref_offset

        # --- M2M fields (list of PKs) ---
        for field_name, ref_model in M2M_FIELDS.get(model, []):
            ref_offset = offsets.get(ref_model, 0)
            if ref_offset > 0 and fields.get(field_name):
                fields[field_name] = [pk + ref_offset for pk in fields[field_name]]

        # --- ImageStore: rewrite source_image path to use target schema ---
        if model == 'app_kit.imagestore' and source_schema and target_schema:
            src_img = fields.get('source_image')
            if src_img and source_schema in src_img:
                fields['source_image'] = src_img.replace(source_schema, target_schema, 1)

        # --- ContentImage: remap object_id via content_type natural key ---
        if model == 'app_kit.contentimage':
            ct = fields.get('content_type')
            if isinstance(ct, list):
                ct_key = tuple(ct)
                ref_model = CONTENT_TYPE_MODEL_MAP.get(ct_key)
                if ref_model:
                    ref_offset = offsets.get(ref_model, 0)
                    if ref_offset > 0 and fields.get('object_id') is not None:
                        fields['object_id'] += ref_offset

        # --- NatureGuidesTaxonTree: rewrite nuid prefix ---
        if model == 'nature_guides.natureguidestaxontree' and old_ng_nuid != new_ng_nuid:
            for nuid_field in ('taxon_nuid', 'source_id'):
                val = fields.get(nuid_field)
                if val and val.startswith(old_ng_nuid):
                    fields[nuid_field] = new_ng_nuid + val[len(old_ng_nuid):]

        # --- MetaNode: rewrite nuid prefix inside children_cache ---
        if model == 'nature_guides.metanode' and old_ng_nuid != new_ng_nuid:
            cache = fields.get('children_cache')
            if cache is not None:
                # children_cache is stored as a JSON object; serialized as a
                # Python dict/list by the fixture loader.  Convert to string,
                # replace, convert back.
                cache_str = json.dumps(cache)
                if old_ng_nuid in cache_str:
                    cache_str = cache_str.replace(old_ng_nuid, new_ng_nuid)
                    fields['children_cache'] = json.loads(cache_str)

    return data


class Command(BaseCommand):
    help = (
        'Import a single Nature Guide ZIP (created by export_nature_guide) '
        'into a target tenant schema without disturbing existing nature guides.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'target_schema',
            type=str,
            help='The tenant schema to import the Nature Guide into.',
        )
        parser.add_argument(
            'zip_path',
            type=str,
            help='Path to the ZIP file produced by export_nature_guide.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Parse and remap the fixture, print a summary, but do not write to the database or filesystem.',
        )

    def handle(self, *args, **options):
        target_schema = options['target_schema']
        zip_path = options['zip_path']
        dry_run = options['dry_run']

        if not os.path.exists(zip_path):
            raise CommandError(f'ZIP file not found: {zip_path}')

        with schema_context(target_schema):
            with tempfile.TemporaryDirectory() as tmp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(tmp_dir)

                # --- Read manifest ---
                manifest_path = os.path.join(tmp_dir, 'manifest.json')
                if not os.path.exists(manifest_path):
                    raise CommandError('manifest.json not found in ZIP')
                with open(manifest_path) as f:
                    manifest = json.load(f)

                source_schema = manifest['source_schema']
                old_ng_pk = manifest['nature_guide_id']
                ng_name = manifest.get('nature_guide_name', str(old_ng_pk))

                # --- Read fixture ---
                data_path = os.path.join(tmp_dir, 'nature_guide_data.json')
                if not os.path.exists(data_path):
                    raise CommandError('nature_guide_data.json not found in ZIP')
                with open(data_path) as f:
                    data = json.load(f)

                # --- Compute PK offsets (must happen inside schema_context) ---
                offsets = _compute_offsets()
                existing_slugs = _collect_existing_slugs()

                new_ng_pk = old_ng_pk + offsets['nature_guides.natureguide']

                nuid_mgr = NuidManager()
                old_ng_nuid = nuid_mgr.decimal_to_nuid(old_ng_pk)
                new_ng_nuid = nuid_mgr.decimal_to_nuid(new_ng_pk)

                self.stdout.write(
                    f'Importing "{ng_name}" (source id={old_ng_pk}) '
                    f'→ target id={new_ng_pk} '
                    f'(nuid prefix {old_ng_nuid!r} → {new_ng_nuid!r})'
                )

                # --- Remap PKs / FKs / nuids / slugs ---
                data = _remap_fixture(data, offsets, old_ng_nuid, new_ng_nuid,
                                      source_schema=source_schema,
                                      target_schema=target_schema)
                data = _deduplicate_slugs(data, existing_slugs)

                # --- Dry-run summary ---
                if dry_run:
                    counts = {}
                    for obj in data:
                        counts[obj['model']] = counts.get(obj['model'], 0) + 1
                    self.stdout.write(self.style.WARNING('DRY RUN — nothing will be written.'))
                    self.stdout.write(f'  NatureGuide "{ng_name}" would be imported as id={new_ng_pk}')
                    self.stdout.write(f'  nuid prefix: {old_ng_nuid!r} → {new_ng_nuid!r}')
                    self.stdout.write('  Objects that would be created:')
                    for model_label, count in sorted(counts.items()):
                        self.stdout.write(f'    {model_label}: {count}')
                    _skip = {'nature_guide_data.json', 'manifest.json'}
                    image_count = sum(
                        1 for r, _, fs in os.walk(tmp_dir)
                        for fn in fs
                        if os.path.relpath(os.path.join(r, fn), tmp_dir) not in _skip
                    )
                    self.stdout.write(f'  Image files that would be copied: {image_count}')
                    self.stdout.write(self.style.WARNING('Dry run complete. No changes made.'))
                    return

                # --- Write modified fixture ---
                modified_path = os.path.join(tmp_dir, 'nature_guide_data_remapped.json')
                with open(modified_path, 'w') as f:
                    json.dump(data, f)

                # --- Load fixture ---
                call_command('loaddata', modified_path, verbosity=1)

                # --- Extract and place images ---
                moved = 0
                skipped = 0
                for root, _dirs, files in os.walk(tmp_dir):
                    for fname in files:
                        src = os.path.join(root, fname)
                        rel = os.path.relpath(src, tmp_dir)

                        # Only copy image files (skip the JSON/manifest we created)
                        if rel in (
                            'nature_guide_data.json',
                            'nature_guide_data_remapped.json',
                            'manifest.json',
                        ):
                            skipped += 1
                            continue

                        # Replace source schema name with target schema name in path
                        rel_target = rel.replace(source_schema, target_schema, 1)
                        dest = os.path.join(settings.MEDIA_ROOT, rel_target)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(src, dest)
                        moved += 1

                self.stdout.write(f'Copied {moved} image file(s), skipped {skipped} file(s).')

        self.stdout.write(
            self.style.SUCCESS(
                f'NatureGuide "{ng_name}" imported successfully into schema "{target_schema}".'
            )
        )

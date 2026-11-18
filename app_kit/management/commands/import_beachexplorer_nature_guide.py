"""
import_beachexplorer_nature_guide
----------------------------------
Imports a BeachExplorer polytomous identification key into a NatureGuide.

Source: PostgreSQL database inside a Docker container (exposed port required).
Mode:   Each parent node gets one DescriptiveTextAndImages MatrixFilter.
        Each child's statement becomes a MatrixFilterSpace; its image (fetched
        from --image-base-url/<filename>) is attached to that space.
        Species leaf results from be_species_tree_branch are added as 'result' nodes.

Usage example:
    python manage.py import_beachexplorer_nature_guide \
        --legacy-host localhost --legacy-port 5433 --legacy-name beachex \
        --legacy-user postgres --legacy-password secret \
        --image-base-url "https://example.com/uploads/species" \
        --schema mytenant \
        --name "BeachExplorer Key" \
        --language de \
        --user-id 1

    # Import without fetching or attaching images
    python manage.py import_beachexplorer_nature_guide \
        --legacy-host localhost --legacy-port 5433 --legacy-name beachex \
        --legacy-user postgres --legacy-password secret \
        --schema mytenant \
        --name "BeachExplorer Key" \
        --language de \
        --no-images

    # Dry-run (env vars): LEGACY_DB_HOST=... LEGACY_DB_NAME=... python manage.py \
    #     import_beachexplorer_nature_guide --schema mytenant --dry-run
"""

import hashlib
import os
import re
import time
import unicodedata
from collections import defaultdict, deque
from urllib.parse import quote

import psycopg2
import psycopg2.extras
import requests

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

from app_kit.features.nature_guides.definitions import TEXT_LENGTH_RESTRICTIONS
from app_kit.features.nature_guides.models import (
    IDENTIFICATION_MODE_POLYTOMOUS,
    ChildrenCacheManager,
    MatrixFilter,
    MatrixFilterSpace,
    MetaNode,
    NatureGuide,
    NatureGuidesTaxonTree,
    NodeFilterSpace,
)
from app_kit.features.object_classes.models import ObjectClass
from app_kit.models import ContentImage, ImageStore
from content_licencing.models import ContentLicenceRegistry
from localcosmos_server.management.commands.beachexplorer_mapping import TAXA_MAP
from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

User = get_user_model()


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

_SQL_BRANCHES = """
    SELECT
        bt.id,
        bt.isentrypoint,
        btt.title,
        btt.statement,
        btt.textnode
    FROM be_tree_branch bt
    LEFT JOIN be_tree_branch_translations btt
        ON btt.translatable_id = bt.id AND btt.locale = %(lang)s
    WHERE bt.deletedat IS NULL
"""

_SQL_RELATIONS = """
    SELECT parent_id, branch_id, levelsort
    FROM be_tree_branch_relation
    WHERE deletedat IS NULL
    ORDER BY parent_id, levelsort
"""

# First image file per branch (via its information blocks), ordered by file position
_SQL_NODE_IMAGES = """
    SELECT DISTINCT ON (btbi.branch_id)
        btbi.branch_id,
        COALESCE(
            bfh.filename || COALESCE(substring(pf.filename from '\.[^.]*$'), ''),
            pf.filename
        ) AS filename,
        pf.copyrightowner,
        pf.author,
        pf.sourceurl
    FROM be_tree_branch__tree_branch_information btbi
    JOIN be_tree_branch_information_file btbif
        ON btbif.information_id = btbi.information_id
    JOIN pd_file pf ON pf.id = btbif.file_id
    LEFT JOIN be_file_hash bfh ON bfh.file_id = pf.id AND bfh.deletedat IS NULL
    ORDER BY btbi.branch_id, btbif.position
"""

_SQL_SPECIES = """
    SELECT
        bstb.tree_brach_id AS branch_id,
        bstb.position,
        COALESCE(bst.name, bs.sciencename) AS display_name,
        bs.sciencename,
        COALESCE(
            bfh.filename || COALESCE(substring(pf.filename from '\.[^.]*$'), ''),
            pf.filename
        ) AS image_filename,
        pf.copyrightowner AS image_copyrightowner,
        pf.author AS image_author,
        pf.sourceurl AS image_sourceurl
    FROM be_species_tree_branch bstb
    JOIN be_species bs ON bs.id = bstb.species_id
    LEFT JOIN be_species_translation bst
        ON bst.translatable_id = bs.id AND bst.locale = %(lang)s
    LEFT JOIN pd_file pf ON pf.id = bs.tree_branch_image
    LEFT JOIN be_file_hash bfh ON bfh.file_id = pf.id AND bfh.deletedat IS NULL
    WHERE bs.deletedat IS NULL
    ORDER BY bstb.tree_brach_id, bstb.position
"""

# Extensions tried (in order) when a DB filename has no extension.
_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp')


def _url_encode_filename(filename):
    """Percent-encode a filename for use in a URL path.

    Normalises to NFC first so that umlauts and other composed characters
    (e.g. ö → U+00F6) are encoded as their single UTF-8 codepoint (%C3%B6)
    rather than as a decomposed base letter + combining mark (o%CC%88).
    """
    return quote(unicodedata.normalize('NFC', filename), safe='/')

# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Import a BeachExplorer identification key as a polytomous NatureGuide'

    def add_arguments(self, parser):
        parser.add_argument(
            '--legacy-host',
            default=os.environ.get('LEGACY_DB_HOST'),
            help='Legacy PostgreSQL host/service name (for Docker Compose, usually the service name).',
        )
        parser.add_argument(
            '--legacy-port',
            type=int,
            default=int(os.environ.get('LEGACY_DB_PORT', '5432')),
            help='Legacy PostgreSQL port. Default: 5432',
        )
        parser.add_argument(
            '--legacy-name',
            default=os.environ.get('LEGACY_DB_NAME'),
            help='Legacy PostgreSQL database name.',
        )
        parser.add_argument(
            '--legacy-user',
            default=os.environ.get('LEGACY_DB_USER'),
            help='Legacy PostgreSQL user.',
        )
        parser.add_argument(
            '--legacy-password',
            default=os.environ.get('LEGACY_DB_PASSWORD'),
            help='Legacy PostgreSQL password.',
        )
        parser.add_argument(
            '--legacy-sslmode',
            default=os.environ.get('LEGACY_DB_SSLMODE'),
            help='Optional PostgreSQL sslmode for legacy DB connection.',
        )
        parser.add_argument(
            '--image-base-url', default=None,
            help='Base URL prepended to pd_file.filename, e.g. https://example.com/uploads (not needed for --dry-run)',
        )
        parser.add_argument(
            '--schema', required=True,
            help='Target tenant schema name',
        )
        parser.add_argument(
            '--name', default=None,
            help='Display name for the new NatureGuide (not needed for --dry-run)',
        )
        parser.add_argument(
            '--language', default='de',
            help='Locale code used to pick translations (default: de)',
        )
        parser.add_argument(
            '--user-id', default=None, type=int,
            help='PK of the user who will own uploaded ImageStore entries (not needed for --dry-run)',
        )
        parser.add_argument(
            '--licence', default='All Rights Reserved',
            help='Licence short name applied to all imported images (default: All Rights Reserved)',
        )
        parser.add_argument(
            '--licence-version', default='1.0',
            help='Licence version applied to all imported images (default: 1.0)',
        )
        parser.add_argument(
            '--no-images', action='store_true',
            help='Skip fetching and attaching imported images. Does not require --image-base-url or --user-id.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Check taxon resolution and overlength node names without writing to the database',
        )

    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        schema = options['schema']
        lang = options['language']
        dry_run = options['dry_run']
        no_images = options['no_images']
        self._no_images = no_images

        legacy_db_config = self._get_legacy_db_config(options)
        be_conn = self._connect_legacy_db(legacy_db_config)
        self.stdout.write(
            f"Connected to legacy DB {legacy_db_config['host']}:{legacy_db_config['port']}/{legacy_db_config['dbname']}"
        )

        if dry_run:
            image_base_url = options['image_base_url'].rstrip('/') if options['image_base_url'] else None
            with schema_context(schema):
                self._run_dry_run(be_conn, lang, image_base_url)
            be_conn.close()
            return

        if not options['name']:
            raise CommandError('--name is required for import (omit only with --dry-run)')
        if options['user_id'] is None and not no_images:
            raise CommandError('--user-id is required for import (omit only with --dry-run or --no-images)')
        if not options['image_base_url'] and not no_images:
            raise CommandError('--image-base-url is required for import (omit only with --dry-run or --no-images)')

        image_base_url = options['image_base_url'].rstrip('/') if options['image_base_url'] else None
        guide_name = options['name']
        user_id = options['user_id']
        self._licence = options['licence']
        self._licence_version = options['licence_version']

        with schema_context(schema):
            user = None
            if not no_images:
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    raise CommandError(f'No user with id={user_id} in schema "{schema}"')

            self._run_import(be_conn, image_base_url, guide_name, lang, user)

        be_conn.close()
        self.stdout.write(self.style.SUCCESS('Import complete.'))

    def _get_legacy_db_config(self, options):
        config = {
            'host': options.get('legacy_host'),
            'port': options.get('legacy_port'),
            'dbname': options.get('legacy_name'),
            'user': options.get('legacy_user'),
            'password': options.get('legacy_password'),
            'sslmode': options.get('legacy_sslmode'),
        }
        missing = [k for k in ['host', 'port', 'dbname', 'user', 'password'] if not config.get(k)]
        if missing:
            raise CommandError(
                'Missing legacy DB connection settings: '
                f'{", ".join(missing)}. Provide --legacy-* arguments or LEGACY_DB_* env vars.'
            )
        return config

    def _connect_legacy_db(self, legacy_db_config):
        connect_kwargs = {
            'host': legacy_db_config['host'],
            'port': legacy_db_config['port'],
            'dbname': legacy_db_config['dbname'],
            'user': legacy_db_config['user'],
            'password': legacy_db_config['password'],
            'connect_timeout': 10,
        }
        if legacy_db_config.get('sslmode'):
            connect_kwargs['sslmode'] = legacy_db_config['sslmode']
        try:
            return psycopg2.connect(**connect_kwargs)
        except psycopg2.OperationalError as exc:
            raise CommandError(f'Cannot connect to legacy database: {exc}') from exc

    # ------------------------------------------------------------------

    def _run_import(self, be_conn, image_base_url, guide_name, lang, user):
        cur = be_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute(_SQL_BRANCHES, {'lang': lang})
        raw_branches = {row['id']: dict(row) for row in cur.fetchall()}

        cur.execute(_SQL_RELATIONS)
        relations_by_parent = defaultdict(list)
        for row in cur.fetchall():
            rel = dict(row)
            relations_by_parent[rel['parent_id']].append(rel)

        cur.execute(_SQL_NODE_IMAGES)
        node_images = {
            row['branch_id']: {
                'filename': row['filename'],
                'copyrightowner': row['copyrightowner'],
                'author': row['author'],
                'sourceurl': row['sourceurl'],
            }
            for row in cur.fetchall()
        }

        cur.execute(_SQL_SPECIES, {'lang': lang})
        species_by_branch = defaultdict(list)
        for row in cur.fetchall():
            species_by_branch[row['branch_id']].append(dict(row))

        cur.close()

        root_be_id = self._find_root(raw_branches)
        self.stdout.write(f'Root branch id: {root_be_id}')

        # Create NatureGuide; NatureGuideManager.create() also creates the root MetaNode/TaxonTree
        ng = NatureGuide.objects.create(guide_name, lang)
        root_node = ng.root_node

        root_data = raw_branches[root_be_id]
        root_node.meta_node.name = self._truncate_text(
            root_data.get('title') or guide_name,
            TEXT_LENGTH_RESTRICTIONS['MetaNode']['name'],
            f'root branch "{root_be_id}" title',
        )
        if root_data.get('textnode'):
            root_node.meta_node.description = root_data['textnode']
        root_node.meta_node.save()

        self.stdout.write(f'Created NatureGuide "{ng}" (pk={ng.pk})')

        branch_nodes_by_be_id = {
            root_be_id: root_node,
        }

        # BFS: (app-kit parent node, BeachEx branch id, ancestry branch ids)
        queue = deque([(root_node, root_be_id, {root_be_id})])

        while queue:
            parent_ng_node, parent_be_id, ancestry = queue.popleft()

            branch_children = sorted(
                relations_by_parent.get(parent_be_id, []),
                key=lambda r: r['levelsort'],
            )
            species_children = species_by_branch.get(parent_be_id, [])

            if not branch_children and not species_children:
                continue

            # Mark parent as polytomous and persist before creating the MatrixFilter
            # (ChildrenCacheManager reads identification_mode from meta_node.settings)
            parent_ng_node.meta_node.add_setting('identification_mode', IDENTIFICATION_MODE_POLYTOMOUS)
            parent_ng_node.meta_node.save()

            mf = MatrixFilter(
                meta_node=parent_ng_node.meta_node,
                name='Merkmale',
                filter_type='DescriptiveTextAndImagesFilter',
                position=0,
            )
            mf.save()

            position = 0

            for rel in branch_children:
                child_be_id = rel['branch_id']
                if child_be_id not in raw_branches:
                    self.stdout.write(
                        self.style.WARNING(f'  Branch {child_be_id} not in branches, skipping')
                    )
                    continue
                if child_be_id in ancestry:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Cycle detected in branch relations ({parent_be_id} -> {child_be_id}), skipping'
                        )
                    )
                    continue

                if child_be_id in branch_nodes_by_be_id:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Reused branch relation ({parent_be_id} -> {child_be_id}), skipping'
                        )
                    )
                    continue

                child_data = raw_branches[child_be_id]
                child_ng_node = self._create_branch_node(
                    ng, parent_ng_node, child_data, position, mf,
                    image_base_url, node_images, user,
                )
                branch_nodes_by_be_id[child_be_id] = child_ng_node
                queue.append((child_ng_node, child_be_id, ancestry | {child_be_id}))
                position += 1

            for sp in species_children:
                self._create_species_node(
                    ng, parent_ng_node, sp, position, mf, image_base_url, user,
                )
                position += 1

            # Rebuild cache once for this parent after all children and spaces are linked;
            # this correctly sets identification_mode and all NodeFilterSpace data.
            ChildrenCacheManager(parent_ng_node.meta_node).rebuild_cache()

    # ------------------------------------------------------------------

    def _create_branch_node(self, ng, parent_ng_node, child_data, position, mf,
                            image_base_url, node_images, user):
        title = self._truncate_text(
            child_data.get('title') or '',
            TEXT_LENGTH_RESTRICTIONS['MetaNode']['name'],
            f'branch "{child_data["id"]}" title',
        )
        statement = child_data.get('statement') or title or str(child_data['id'])

        child_meta_node = MetaNode(
            nature_guide=ng,
            name=title or None,
            node_type='node',
            description=child_data.get('textnode') or None,
        )
        child_meta_node.save()

        child_ng_node = NatureGuidesTaxonTree(
            nature_guide=ng,
            meta_node=child_meta_node,
            position=position,
        )
        child_ng_node.save(parent_ng_node)

        mfs = self._create_filter_space(mf, statement, position)

        if not self._no_images:
            img = node_images.get(child_data['id'])
            if img:
                self._attach_image(image_base_url, img['filename'], user, mfs,
                                   copyrightowner=img['copyrightowner'],
                                   author=img['author'],
                                   sourceurl=img['sourceurl'])

        self._link_node_to_space(child_ng_node, mf, mfs)

        self.stdout.write(f'  + node "{title}" (be_id={child_data["id"]})')
        return child_ng_node

    def _create_species_node(self, ng, parent_ng_node, sp, position, mf,
                             image_base_url, user):
        base_display_name = sp.get('display_name') or sp.get('sciencename') or 'Unknown'
        display_name = self._truncate_text(
            base_display_name,
            TEXT_LENGTH_RESTRICTIONS['MetaNode']['name'],
            f'species "{sp.get("sciencename") or "unknown"}" display_name',
        )

        result_meta_node = MetaNode(
            nature_guide=ng,
            name=display_name,
            node_type='result',
        )

        resolution = self._resolve_taxon(sp.get('sciencename'))
        resolved_taxon = resolution.get('taxon')
        if resolution['status'] in ('not_found', 'mapped_missing'):
            self.stdout.write(self.style.WARNING(f'    Taxon not found: "{sp.get("sciencename")}"'))

        if resolved_taxon:
            result_meta_node.set_taxon(LazyTaxon(instance=resolved_taxon))

        mapped_morphotype = resolution.get('morphotype')
        has_assigned_morphotype = False
        if mapped_morphotype:
            morphotype_obj = self._find_morphotype(mapped_morphotype)
            if morphotype_obj:
                result_meta_node.morphotype = morphotype_obj
                has_assigned_morphotype = True
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'    Morphotype not found for "{sp.get("sciencename") or "unknown"}": "{mapped_morphotype}"'
                    )
                )

        mapped_object_class = resolution.get('object_class')
        has_assigned_object_class = False
        if mapped_object_class:
            object_class = self._find_object_class(mapped_object_class)
            if object_class:
                result_meta_node.object_class = object_class
                has_assigned_object_class = True
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'    Object class not found for "{sp.get("sciencename")}": "{mapped_object_class}"'
                    )
                )

        if resolved_taxon and (has_assigned_morphotype or has_assigned_object_class):
            preferred_locale_name = self._get_preferred_taxon_locale_name(resolved_taxon, language='de')
            if preferred_locale_name:
                display_name = self._truncate_text(
                    preferred_locale_name,
                    TEXT_LENGTH_RESTRICTIONS['MetaNode']['name'],
                    f'species "{sp.get("sciencename") or "unknown"}" preferred locale name',
                )
                result_meta_node.name = display_name

        result_meta_node.save()

        result_ng_node = NatureGuidesTaxonTree(
            nature_guide=ng,
            meta_node=result_meta_node,
            position=position,
        )
        result_ng_node.save(parent_ng_node)

        mfs = self._create_filter_space(mf, display_name, position)

        if not self._no_images and sp.get('image_filename'):
            self._attach_image(image_base_url, sp['image_filename'], user, mfs,
                               copyrightowner=sp.get('image_copyrightowner'),
                               author=sp.get('image_author'),
                               sourceurl=sp.get('image_sourceurl'))

        self._link_node_to_space(result_ng_node, mf, mfs)

        self.stdout.write(f'  + result "{display_name}"')
        return result_ng_node

    # ------------------------------------------------------------------

    def _truncate_text(self, text, max_length, label):
        if text is None:
            return None
        if len(text) <= max_length:
            return text

        truncated = text[:max_length]
        self.stdout.write(
            self.style.WARNING(
                f'  Truncated {label} to {max_length} characters: "{truncated}"'
            )
        )
        return truncated

    def _create_filter_space(self, mf, text, position):
        mfs = MatrixFilterSpace(
            matrix_filter=mf,
            encoded_space=text,
            position=position,
        )
        mfs.save()
        return mfs

    def _link_node_to_space(self, ng_node, mf, mfs):
        nfs = NodeFilterSpace(node=ng_node, matrix_filter=mf)
        nfs.save()
        nfs.values.add(mfs)

    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_taxon_name(name):
        if not name:
            return ''

        normalized = unicodedata.normalize('NFKC', name).strip().lower()
        normalized = re.sub(r'\s*/\s*', '/', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    def _find_taxa_map_mapping(self, sciencename):
        if not sciencename:
            return None, None

        mapping = TAXA_MAP.get(sciencename)
        if mapping:
            return sciencename, mapping

        stripped = sciencename.strip()
        if stripped != sciencename:
            mapping = TAXA_MAP.get(stripped)
            if mapping:
                return stripped, mapping

        normalized_name = self._normalize_taxon_name(sciencename)
        if not normalized_name:
            return None, None

        if not hasattr(self, '_normalized_taxa_map'):
            normalized_taxa_map = {}
            for map_key, map_value in TAXA_MAP.items():
                normalized_key = self._normalize_taxon_name(map_key)
                if normalized_key and normalized_key not in normalized_taxa_map:
                    normalized_taxa_map[normalized_key] = (map_key, map_value)
            self._normalized_taxa_map = normalized_taxa_map

        return self._normalized_taxa_map.get(normalized_name, (None, None))

    def _resolve_taxon(self, sciencename):
        """Returns a resolution dict; does not log — callers decide what to do."""
        result = {
            'status': 'not_found',
            'taxon': None,
            'mapped_name': None,
            'morphotype': None,
            'object_class': None,
            'in_taxa_map': False,
            'in_custom_taxonomy': False,
            'mapped_in_custom_taxonomy': False,
            'taxa_map_key': None,
        }
        if not sciencename:
            return result

        models = self._get_taxonomy_models()
        taxon = models.TaxonTreeModel.objects.filter(taxon_latname=sciencename).first()
        if taxon:
            result.update(status='found', taxon=taxon, in_custom_taxonomy=True)
            return result

        map_key, mapping = self._find_taxa_map_mapping(sciencename)
        if mapping:
            result['in_taxa_map'] = True
            result['taxa_map_key'] = map_key
            result['mapped_name'] = mapping.get('new_taxon')
            result['morphotype'] = mapping.get('morphotype')
            result['object_class'] = mapping.get('object_class')
            if result['mapped_name']:
                taxon = models.TaxonTreeModel.objects.filter(
                    taxon_latname=result['mapped_name']
                ).first()
                result['taxon'] = taxon
                result['mapped_in_custom_taxonomy'] = bool(taxon)
                result['status'] = 'mapped' if taxon else 'mapped_missing'

        return result

    def _get_taxonomy_models(self):
        if not hasattr(self, '_taxonomy_models'):
            self._taxonomy_models = TaxonomyModelRouter('taxonomy.sources.custom')
        return self._taxonomy_models

    def _get_preferred_taxon_locale_name(self, taxon, language='de'):
        if not taxon:
            return None

        if not hasattr(self, '_taxon_locale_name_cache'):
            self._taxon_locale_name_cache = {}

        cache_key = (taxon.pk, language)
        if cache_key in self._taxon_locale_name_cache:
            return self._taxon_locale_name_cache[cache_key]

        models = self._get_taxonomy_models()
        locale = models.TaxonLocaleModel.objects.filter(
            taxon=taxon,
            language=language,
            preferred=True,
        ).first()

        if not locale:
            locale = models.TaxonLocaleModel.objects.filter(
                taxon=taxon,
                language=language,
            ).order_by('pk').first()

        locale_name = locale.name if locale else None
        self._taxon_locale_name_cache[cache_key] = locale_name
        return locale_name

    def _find_custom_taxon(self, sciencename):
        resolution = self._resolve_taxon(sciencename)
        if resolution['status'] == 'not_found' or resolution['status'] == 'mapped_missing':
            self.stdout.write(self.style.WARNING(f'    Taxon not found: "{sciencename}"'))
        return resolution['taxon']

    def _find_object_class(self, object_class_value):
        if not object_class_value:
            return None

        if not hasattr(self, '_object_class_cache'):
            self._object_class_cache = {}

        cache_key = object_class_value
        if cache_key in self._object_class_cache:
            return self._object_class_cache[cache_key]

        candidates = [object_class_value]
        stripped = object_class_value.strip()
        if stripped and stripped not in candidates:
            candidates.append(stripped)

        normalized_scientific_name = stripped.lower().replace(' ', '_') if stripped else None
        if normalized_scientific_name and normalized_scientific_name not in candidates:
            candidates.append(normalized_scientific_name)

        object_class = None
        for scientific_name in candidates:
            object_class = ObjectClass.objects.filter(category='object_class', scientific_name=scientific_name).order_by('pk').first()
            if object_class:
                break

        if not object_class:
            object_class = (
                ObjectClass.objects.filter(category='object_class', name__iexact=stripped).order_by('pk').first()
                if stripped else None
            )

        self._object_class_cache[cache_key] = object_class
        return object_class

    def _find_morphotype(self, morphotype_value):
        if not morphotype_value:
            return None

        if not hasattr(self, '_morphotype_cache'):
            self._morphotype_cache = {}

        cache_key = morphotype_value
        if cache_key in self._morphotype_cache:
            return self._morphotype_cache[cache_key]

        candidates = [morphotype_value]
        stripped = morphotype_value.strip()
        if stripped and stripped not in candidates:
            candidates.append(stripped)

        normalized_scientific_name = stripped.lower().replace(' ', '_') if stripped else None
        if normalized_scientific_name and normalized_scientific_name not in candidates:
            candidates.append(normalized_scientific_name)

        morphotype = None
        for scientific_name in candidates:
            morphotype = ObjectClass.objects.filter(category='morphotype', scientific_name=scientific_name).order_by('pk').first()
            if morphotype:
                break

        if not morphotype:
            morphotype = (
                ObjectClass.objects.filter(category='morphotype', name__iexact=stripped).order_by('pk').first()
                if stripped else None
            )

        self._morphotype_cache[cache_key] = morphotype
        return morphotype

    def _run_dry_run(self, be_conn, lang, image_base_url=None):
        cur = be_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(_SQL_BRANCHES, {'lang': lang})
        raw_branches = [dict(row) for row in cur.fetchall()]
        raw_branches_by_id = {branch['id']: branch for branch in raw_branches}

        cur.execute(_SQL_RELATIONS)
        relations_by_parent = defaultdict(list)
        for row in cur.fetchall():
            relations_by_parent[row['parent_id']].append(row['branch_id'])

        cur.execute(_SQL_NODE_IMAGES)
        node_images = {
            row['branch_id']: {'filename': row['filename']}
            for row in cur.fetchall()
            if row['filename']
        }

        cur.execute(_SQL_SPECIES, {'lang': lang})
        species_rows = [dict(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT bs.sciencename
            FROM be_species_tree_branch bstb
            JOIN be_species bs ON bs.id = bstb.species_id
            WHERE bs.deletedat IS NULL
            ORDER BY bs.sciencename
        """)
        sciencenames = [row['sciencename'] for row in cur.fetchall()]
        cur.close()

        found, mapped, mapped_missing, not_found = [], [], [], []
        verbose_details = []

        for name in sciencenames:
            r = self._resolve_taxon(name)
            verbose_details.append({
                'name': name,
                'status': r['status'],
                'in_taxa_map': r.get('in_taxa_map', False),
                'in_custom_taxonomy': r.get('in_custom_taxonomy', False),
                'mapped_name': r.get('mapped_name'),
                'morphotype': r.get('morphotype'),
                'object_class': r.get('object_class'),
                'mapped_in_custom_taxonomy': r.get('mapped_in_custom_taxonomy', False),
                'taxa_map_key': r.get('taxa_map_key'),
            })
            if r['status'] == 'found':
                found.append(name)
            elif r['status'] == 'mapped':
                mapped.append(r)
                r['original'] = name
            elif r['status'] == 'mapped_missing':
                mapped_missing.append(r)
                r['original'] = name
            else:
                not_found.append(name)

        total = len(sciencenames)
        coverage_ok = []
        coverage_missing = []
        for detail in verbose_details:
            if detail['in_custom_taxonomy'] or detail['in_taxa_map']:
                coverage_ok.append(detail['name'])
            else:
                coverage_missing.append(detail['name'])

        self.stdout.write(f'\nDry-run taxon check — {total} unique species')
        self.stdout.write('=' * 50)

        self.stdout.write('\nSpecies lookup coverage (custom taxonomy OR TAXA_MAP):')
        if not coverage_missing:
            self.stdout.write(
                self.style.SUCCESS(
                    f'  OK: all {len(coverage_ok)} species occur in custom taxonomy or TAXA_MAP.'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'  MISSING ({len(coverage_missing)}): these species are in neither custom taxonomy nor TAXA_MAP:'
                )
            )
            for name in coverage_missing:
                self.stdout.write(f'  - {name}')

        self.stdout.write('\nLookup details:')
        for detail in verbose_details:
            name = detail['name']
            mapping_text = 'yes' if detail['in_taxa_map'] else 'no'
            custom_text = 'yes' if detail['in_custom_taxonomy'] else 'no'
            mapped_target_text = 'n/a'
            if detail['mapped_name']:
                mapped_target_text = 'yes' if detail['mapped_in_custom_taxonomy'] else 'no'
            morphotype_assigned = 'yes' if detail.get('morphotype') else 'no'
            object_class_assigned = 'yes' if detail.get('object_class') else 'no'

            self.stdout.write(
                f"  - {name}: status={detail['status']}; TAXA_MAP={mapping_text}; "
                f"custom_taxonomy={custom_text}; mapped_target={mapped_target_text}; "
                f"morphotype_assigned={morphotype_assigned}; object_class_assigned={object_class_assigned}"
                f"{f'; mapped_name={detail['mapped_name']}' if detail['mapped_name'] else ''}"
                f"{f'; morphotype={detail['morphotype']}' if detail.get('morphotype') else ''}"
                f"{f'; object_class={detail['object_class']}' if detail.get('object_class') else ''}"
                f"{f'; map_key={detail['taxa_map_key']}' if detail['taxa_map_key'] and detail['taxa_map_key'] != name else ''}"
            )

        if found:
            self.stdout.write(self.style.SUCCESS(f'\nFOUND directly ({len(found)}):'))
            for name in found:
                self.stdout.write(f'  - {name}')

        if mapped:
            self.stdout.write(self.style.WARNING(f'\nMAPPED via TAXA_MAP ({len(mapped)}):'))
            for r in mapped:
                extras = self._format_map_extras(r)
                self.stdout.write(f'  - {r["original"]} -> {r["mapped_name"]}{extras}')

        if mapped_missing:
            self.stdout.write(self.style.ERROR(f'\nMAPPED but target missing in custom taxonomy ({len(mapped_missing)}):'))
            for r in mapped_missing:
                extras = self._format_map_extras(r)
                self.stdout.write(f'  - {r["original"]} -> {r["mapped_name"]}  [TARGET MISSING{extras}]')

        if not_found:
            self.stdout.write(self.style.ERROR(f'\nNOT FOUND ({len(not_found)}):'))
            for name in not_found:
                self.stdout.write(f'  - {name}')

        self.stdout.write(
            f'\nSummary: {len(found)} direct, {len(mapped)} mapped, '
            f'{len(mapped_missing)} mapped-missing, {len(not_found)} not found'
        )

        self.stdout.write('\nMorphotype DB validation:')
        morphotype_strings = {
            d['morphotype'] for d in verbose_details if d.get('morphotype')
        }
        if not morphotype_strings:
            self.stdout.write('  No morphotypes referenced in TAXA_MAP.')
        else:
            missing_morphotypes = []
            for m in sorted(morphotype_strings):
                if not self._find_morphotype(m):
                    missing_morphotypes.append(m)
            if missing_morphotypes:
                self.stdout.write(self.style.ERROR(f'  MISSING ({len(missing_morphotypes)}) morphotypes not found in ObjectClass:'))
                for m in missing_morphotypes:
                    self.stdout.write(f'  - {m}')
            else:
                self.stdout.write(self.style.SUCCESS(f'  OK: all {len(morphotype_strings)} morphotype(s) resolved to ObjectClass entries.'))

        self.stdout.write('\nObject class DB validation:')
        object_class_strings = {
            d['object_class'] for d in verbose_details if d.get('object_class')
        }
        if not object_class_strings:
            self.stdout.write('  No object classes referenced in TAXA_MAP.')
        else:
            missing_object_classes = []
            wrong_category = []
            for oc in sorted(object_class_strings):
                if not self._find_object_class(oc):
                    # check whether it accidentally exists as a morphotype
                    if self._find_morphotype(oc):
                        wrong_category.append(oc)
                    else:
                        missing_object_classes.append(oc)
            if wrong_category:
                self.stdout.write(self.style.ERROR(f'  WRONG CATEGORY ({len(wrong_category)}) — these exist as morphotype, not object_class:'))
                for oc in wrong_category:
                    self.stdout.write(f'  - {oc}')
            if missing_object_classes:
                self.stdout.write(self.style.ERROR(f'  MISSING ({len(missing_object_classes)}) object classes not found in ObjectClass:'))
                for oc in missing_object_classes:
                    self.stdout.write(f'  - {oc}')
            if not wrong_category and not missing_object_classes:
                self.stdout.write(self.style.SUCCESS(f'  OK: all {len(object_class_strings)} object class(es) resolved to ObjectClass entries.'))

        cycle_entries = self._find_relation_cycles(raw_branches_by_id, relations_by_parent)
        self.stdout.write('\nRelation cycle check:')
        if not cycle_entries:
            self.stdout.write(self.style.SUCCESS('  No cycles found in be_tree_branch_relation.'))
        else:
            for cycle in cycle_entries:
                cycle_path = ' -> '.join(str(node_id) for node_id in cycle['path'])
                self.stdout.write(
                    self.style.ERROR(
                        f'  - cycle edge {cycle["parent"]} -> {cycle["child"]}; path: {cycle_path}'
                    )
                )

        root_be_id = self._find_root(raw_branches_by_id)
        skipped_relations = self._collect_skipped_relations_for_import(
            root_be_id, raw_branches_by_id, relations_by_parent
        )
        self.stdout.write('\nSkipped relations in import traversal:')
        if not skipped_relations:
            self.stdout.write(self.style.SUCCESS('  No relations would be skipped.'))
        else:
            for relation in skipped_relations:
                message = (
                    f'  - {relation["parent"]} ("{relation["parent_name"]}") -> '
                    f'{relation["child"]} ("{relation["child_name"]}", type={relation["child_node_type"]}): '
                    f'{relation["reason"]}'
                )
                if relation.get('earlier_parent') is not None:
                    message = (
                        f'{message}; earlier parent: {relation["earlier_parent"]} '
                        f'("{relation["earlier_parent_name"]}")'
                    )
                self.stdout.write(
                    self.style.WARNING(
                        message
                    )
                )

        name_max_length = TEXT_LENGTH_RESTRICTIONS['MetaNode']['name']
        overlength_entries = []

        for branch in raw_branches:
            branch_title = branch.get('title') or ''
            if len(branch_title) > name_max_length:
                overlength_entries.append({
                    'entry_type': 'branch',
                    'identifier': branch['id'],
                    'value': branch_title,
                })

        for species in species_rows:
            display_name = species.get('display_name') or species.get('sciencename') or 'Unknown'
            if len(display_name) > name_max_length:
                overlength_entries.append({
                    'entry_type': 'species',
                    'identifier': species.get('sciencename') or species.get('branch_id'),
                    'value': display_name,
                })

        self.stdout.write(f'\nOverlength names check (max {name_max_length} chars):')
        if not overlength_entries:
            self.stdout.write(self.style.SUCCESS('  No overlength names found.'))
        else:
            seen = set()
            for entry in overlength_entries:
                dedupe_key = (entry['entry_type'], entry['identifier'], entry['value'])
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                self.stdout.write(
                    self.style.WARNING(
                        f'  - {entry["entry_type"]} {entry["identifier"]}: '
                        f'{len(entry["value"])} chars -> "{entry["value"]}"'
                    )
                )

        all_filenames = set()
        for img in node_images.values():
            if img.get('filename'):
                all_filenames.add(img['filename'])
        for sp in species_rows:
            if sp.get('image_filename'):
                all_filenames.add(sp['image_filename'])

        missing_images = []
        self.stdout.write(f'\nImage availability check ({len(all_filenames)} unique filenames in DB):')
        if not image_base_url:
            self.stdout.write('  Skipped — provide --image-base-url to enable this check.')
        elif not all_filenames:
            self.stdout.write('  No image filenames found in DB.')
        else:
            for filename in sorted(all_filenames):
                ok, resolved_url = self._check_image_url(image_base_url, filename)
                encoded_url = f'{image_base_url}/{_url_encode_filename(filename)}'
                if ok:
                    note = f' (resolved to {resolved_url})' if resolved_url != encoded_url else ''
                    self.stdout.write(self.style.SUCCESS(f'  OK: {filename}{note}'))
                else:
                    missing_images.append(filename)
                    self.stdout.write(self.style.ERROR(f'  MISSING: {filename}'))
                time.sleep(0.5)
            if missing_images:
                self.stdout.write(self.style.ERROR(
                    f'\n  {len(missing_images)}/{len(all_filenames)} images not accessible at {image_base_url}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'\n  All {len(all_filenames)} images accessible.'
                ))

        # Build species-by-branch lookup (same logic as the actual import)
        species_by_branch_dr = defaultdict(list)
        for row in species_rows:
            species_by_branch_dr[row['branch_id']].append(row)

        duplicate_parents = []
        for parent_id, child_ids in relations_by_parent.items():
            parent_data = raw_branches_by_id.get(parent_id)
            parent_name = (parent_data.get('title') or str(parent_id)) if parent_data else str(parent_id)

            # Collect all child names for this parent
            child_names = []
            for child_id in child_ids:
                child_data = raw_branches_by_id.get(child_id)
                if child_data:
                    child_names.append(child_data.get('title') or str(child_id))
            for sp in species_by_branch_dr.get(parent_id, []):
                child_names.append(
                    sp.get('display_name') or sp.get('sciencename') or str(sp.get('branch_id'))
                )

            seen_names = {}
            for name in child_names:
                seen_names.setdefault(name, 0)
                seen_names[name] += 1

            dupes = {name: count for name, count in seen_names.items() if count > 1}
            if dupes:
                duplicate_parents.append({
                    'parent_id': parent_id,
                    'parent_name': parent_name,
                    'dupes': dupes,
                })

        self.stdout.write('\nDuplicate children check (same name under one parent):')
        if not duplicate_parents:
            self.stdout.write(self.style.SUCCESS('  No duplicate child names found.'))
        else:
            for entry in duplicate_parents:
                self.stdout.write(
                    self.style.WARNING(
                        f'  - parent {entry["parent_id"]} ("{entry["parent_name"]}"): '
                        + ', '.join(
                            f'"{name}" × {count}'
                            for name, count in sorted(entry['dupes'].items())
                        )
                    )
                )

        if missing_images:
            self.stdout.write(self.style.ERROR(
                f'\n--- Missing images ({len(missing_images)}) ---'
            ))
            for filename in missing_images:
                self.stdout.write(self.style.ERROR(f'  {filename}'))

    def _check_image_url(self, base_url, filename):
        """
        Check whether base_url/filename is reachable.  When the filename has no
        extension, also try common image extensions so that extension-less DB
        entries still resolve.  Tries HEAD first; falls back to a streaming GET
        (body never downloaded) when the server returns 405 Method Not Allowed.
        Retries up to 3 times on 429 Too Many Requests (honouring Retry-After)
        and on transient connection errors (exponential back-off), to handle
        servers that temporarily drop connections under load.
        Returns (accessible: bool, resolved_url: str | None).
        """
        candidates = [filename]
        if not os.path.splitext(filename)[1]:
            candidates += [filename + ext for ext in _IMAGE_EXTENSIONS]

        for candidate in candidates:
            url = f'{base_url}/{_url_encode_filename(candidate)}'
            for attempt in range(3):
                try:
                    resp = requests.head(url, timeout=10, allow_redirects=True)
                    if resp.status_code == 405:
                        # Server does not support HEAD; fall back to a streaming GET.
                        # stream=True means the body is never downloaded regardless of file size.
                        resp = requests.get(url, timeout=10, allow_redirects=True, stream=True)
                        resp.close()
                    if resp.status_code == 429:
                        wait = int(resp.headers.get('Retry-After', 10 * (attempt + 1)))
                        self.stdout.write(f'    Rate-limited; waiting {wait}s before retry…')
                        time.sleep(wait)
                        continue
                    if resp.status_code < 400:
                        return True, url
                    break  # definitive non-429 HTTP error; don't retry
                except requests.RequestException as exc:
                    if attempt < 2:
                        wait = 10 * (attempt + 1)
                        self.stdout.write(f'    Connection error ({exc}); waiting {wait}s before retry…')
                        time.sleep(wait)
                    # on the final attempt fall through to return False

        return False, None

    @staticmethod
    def _find_relation_cycles(raw_branches_by_id, relations_by_parent):
        colors = {}
        cycle_entries = []
        seen_cycles = set()

        for start_node in raw_branches_by_id.keys():
            if colors.get(start_node, 0) != 0:
                continue

            colors[start_node] = 1
            path = [start_node]
            path_index = {start_node: 0}
            stack = [(start_node, iter(relations_by_parent.get(start_node, [])))]

            while stack:
                current_node, child_iterator = stack[-1]
                try:
                    child_node = next(child_iterator)
                except StopIteration:
                    colors[current_node] = 2
                    stack.pop()
                    path_index.pop(current_node, None)
                    path.pop()
                    continue

                if child_node not in raw_branches_by_id:
                    continue

                child_color = colors.get(child_node, 0)
                if child_color == 0:
                    colors[child_node] = 1
                    path.append(child_node)
                    path_index[child_node] = len(path) - 1
                    stack.append((child_node, iter(relations_by_parent.get(child_node, []))))
                elif child_color == 1:
                    cycle_path = tuple(path[path_index[child_node]:] + [child_node])
                    if cycle_path in seen_cycles:
                        continue
                    seen_cycles.add(cycle_path)
                    cycle_entries.append({
                        'parent': current_node,
                        'child': child_node,
                        'path': list(cycle_path),
                    })

        return cycle_entries

    @staticmethod
    def _collect_skipped_relations_for_import(root_be_id, raw_branches_by_id, relations_by_parent):
        skipped_relations = []
        branch_nodes_by_be_id = {root_be_id}
        first_parent_by_child = {}
        queue = deque([(root_be_id, {root_be_id})])

        while queue:
            parent_be_id, ancestry = queue.popleft()
            for child_be_id in relations_by_parent.get(parent_be_id, []):
                parent_name = (raw_branches_by_id.get(parent_be_id, {}).get('title') or '').strip() or str(parent_be_id)
                if child_be_id not in raw_branches_by_id:
                    skipped_relations.append({
                        'parent': parent_be_id,
                        'parent_name': parent_name,
                        'child': child_be_id,
                        'child_name': 'missing branch',
                        'child_node_type': 'unknown',
                        'reason': 'branch_id missing in branches table',
                    })
                    continue
                child_name = (raw_branches_by_id.get(child_be_id, {}).get('title') or '').strip() or str(child_be_id)
                if child_be_id in ancestry:
                    skipped_relations.append({
                        'parent': parent_be_id,
                        'parent_name': parent_name,
                        'child': child_be_id,
                        'child_name': child_name,
                        'child_node_type': 'node',
                        'reason': 'cycle edge',
                    })
                    continue
                if child_be_id in branch_nodes_by_be_id:
                    earlier_parent = first_parent_by_child.get(child_be_id)
                    earlier_parent_name = (
                        (raw_branches_by_id.get(earlier_parent, {}).get('title') or '').strip() or str(earlier_parent)
                    ) if earlier_parent is not None else None
                    skipped_relations.append({
                        'parent': parent_be_id,
                        'parent_name': parent_name,
                        'child': child_be_id,
                        'child_name': child_name,
                        'child_node_type': 'node',
                        'reason': 'reused branch (already attached to earlier parent)',
                        'earlier_parent': earlier_parent,
                        'earlier_parent_name': earlier_parent_name,
                    })
                    continue

                branch_nodes_by_be_id.add(child_be_id)
                first_parent_by_child[child_be_id] = parent_be_id
                queue.append((child_be_id, ancestry | {child_be_id}))

        return skipped_relations

    @staticmethod
    def _format_map_extras(resolution):
        parts = []
        if resolution.get('morphotype'):
            parts.append(f'morphotype: {resolution["morphotype"]}')
        if resolution.get('object_class'):
            parts.append(f'object_class: {resolution["object_class"]}')
        return ('  [' + ', '.join(parts) + ']') if parts else ''

    # ------------------------------------------------------------------

    def _attach_image(self, base_url, filename, user, content_obj,
                       copyrightowner=None, author=None, sourceurl=None):
        if self._no_images:
            return

        url = f'{base_url}/{_url_encode_filename(filename)}'
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            self.stdout.write(self.style.WARNING(f'    Could not fetch {url}: {exc}'))
            return

        data = resp.content
        md5 = hashlib.md5(data).hexdigest()

        # Reuse an existing ImageStore entry if this file was already imported
        image_store = ImageStore.objects.filter(md5=md5, uploaded_by=user).first()
        if not image_store:
            ext = os.path.splitext(filename)[-1] or '.jpg'
            image_store = ImageStore(uploaded_by=user, md5=md5)
            # md5 must be set before source_image.save so upload_to path is computed correctly
            image_store.source_image.save(f'{md5}{ext}', ContentFile(data), save=False)
            image_store.save()

        creator_name = author or user.get_full_name() or user.username
        ContentLicenceRegistry.objects.register(
            image_store,
            'source_image',
            user,
            self._licence,
            self._licence_version,
            creator_name=creator_name,
            source_link=sourceurl or None,
        )

        content_type = ContentType.objects.get_for_model(content_obj.__class__)
        ContentImage.objects.create(
            image_store=image_store,
            content_type=content_type,
            object_id=content_obj.pk,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _find_root(branches):
        roots = [b_id for b_id, b in branches.items() if b.get('isentrypoint')]
        if not roots:
            raise CommandError('No entry-point branch found (isentrypoint=true)')
        if len(roots) > 1:
            raise CommandError(f'Multiple entry-point branches found: {roots}')
        return roots[0]

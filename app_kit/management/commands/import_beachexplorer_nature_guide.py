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

    # Dry-run (env vars): LEGACY_DB_HOST=... LEGACY_DB_NAME=... python manage.py \
    #     import_beachexplorer_nature_guide --schema mytenant --dry-run
"""

import hashlib
import os
import re
import unicodedata
from collections import defaultdict, deque

import psycopg2
import psycopg2.extras
import requests

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

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
        pf.filename,
        pf.copyrightowner,
        pf.author,
        pf.sourceurl
    FROM be_tree_branch__tree_branch_information btbi
    JOIN be_tree_branch_information_file btbif
        ON btbif.information_id = btbi.information_id
    JOIN pd_file pf ON pf.id = btbif.file_id
    ORDER BY btbi.branch_id, btbif.position
"""

_SQL_SPECIES = """
    SELECT
        bstb.tree_brach_id AS branch_id,
        bstb.position,
        COALESCE(bst.name, bs.sciencename) AS display_name,
        bs.sciencename,
        pf.filename AS image_filename,
        pf.copyrightowner AS image_copyrightowner,
        pf.author AS image_author,
        pf.sourceurl AS image_sourceurl
    FROM be_species_tree_branch bstb
    JOIN be_species bs ON bs.id = bstb.species_id
    LEFT JOIN be_species_translation bst
        ON bst.translatable_id = bs.id AND bst.locale = %(lang)s
    LEFT JOIN pd_file pf ON pf.id = bs.tree_branch_image
    WHERE bs.deletedat IS NULL
    ORDER BY bstb.tree_brach_id, bstb.position
"""


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
            '--dry-run', action='store_true',
            help='Check taxon resolution without writing to the database',
        )

    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        schema = options['schema']
        lang = options['language']
        dry_run = options['dry_run']

        legacy_db_config = self._get_legacy_db_config(options)
        be_conn = self._connect_legacy_db(legacy_db_config)
        self.stdout.write(
            f"Connected to legacy DB {legacy_db_config['host']}:{legacy_db_config['port']}/{legacy_db_config['dbname']}"
        )

        if dry_run:
            with schema_context(schema):
                self._run_dry_run(be_conn, lang)
            be_conn.close()
            return

        if not options['name']:
            raise CommandError('--name is required for import (omit only with --dry-run)')
        if options['user_id'] is None:
            raise CommandError('--user-id is required for import (omit only with --dry-run)')
        if not options['image_base_url']:
            raise CommandError('--image-base-url is required for import (omit only with --dry-run)')

        image_base_url = options['image_base_url'].rstrip('/')
        guide_name = options['name']
        user_id = options['user_id']
        self._licence = options['licence']
        self._licence_version = options['licence_version']

        with schema_context(schema):
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
            relations_by_parent[row['parent_id']].append(dict(row))

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
        root_node.meta_node.name = root_data.get('title') or guide_name
        if root_data.get('textnode'):
            root_node.meta_node.description = root_data['textnode']
        root_node.meta_node.save()

        self.stdout.write(f'Created NatureGuide "{ng}" (pk={ng.pk})')

        # BFS: (app-kit parent node, BeachEx branch id)
        queue = deque([(root_node, root_be_id)])

        while queue:
            parent_ng_node, parent_be_id = queue.popleft()

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
                name=parent_ng_node.meta_node.name or 'Select',
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

                child_data = raw_branches[child_be_id]
                child_ng_node = self._create_branch_node(
                    ng, parent_ng_node, child_data, position, mf,
                    image_base_url, node_images, user,
                )
                queue.append((child_ng_node, child_be_id))
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
        title = child_data.get('title') or ''
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
            decision_rule=child_data.get('statement') or None,
            position=position,
        )
        child_ng_node.save(parent_ng_node)

        mfs = self._create_filter_space(mf, statement, position)

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
        display_name = sp.get('display_name') or sp.get('sciencename') or 'Unknown'

        result_meta_node = MetaNode(
            nature_guide=ng,
            name=display_name,
            node_type='result',
        )

        taxon = self._find_custom_taxon(sp.get('sciencename'))
        if taxon:
            result_meta_node.set_taxon(LazyTaxon(instance=taxon))

        result_meta_node.save()

        result_ng_node = NatureGuidesTaxonTree(
            nature_guide=ng,
            meta_node=result_meta_node,
            decision_rule=None,
            position=position,
        )
        result_ng_node.save(parent_ng_node)

        mfs = self._create_filter_space(mf, display_name, position)

        if sp.get('image_filename'):
            self._attach_image(image_base_url, sp['image_filename'], user, mfs,
                               copyrightowner=sp.get('image_copyrightowner'),
                               author=sp.get('image_author'),
                               sourceurl=sp.get('image_sourceurl'))

        self._link_node_to_space(result_ng_node, mf, mfs)

        self.stdout.write(f'  + result "{display_name}"')
        return result_ng_node

    # ------------------------------------------------------------------

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

        models = TaxonomyModelRouter('taxonomy.sources.custom')
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

    def _find_custom_taxon(self, sciencename):
        resolution = self._resolve_taxon(sciencename)
        if resolution['status'] == 'not_found' or resolution['status'] == 'mapped_missing':
            self.stdout.write(self.style.WARNING(f'    Taxon not found: "{sciencename}"'))
        return resolution['taxon']

    def _run_dry_run(self, be_conn, lang):
        cur = be_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
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
        self.stdout.write(f'\nDry-run taxon check — {total} unique species')
        self.stdout.write('=' * 50)

        self.stdout.write('\nLookup details:')
        for detail in verbose_details:
            name = detail['name']
            mapping_text = 'yes' if detail['in_taxa_map'] else 'no'
            custom_text = 'yes' if detail['in_custom_taxonomy'] else 'no'
            mapped_target_text = 'n/a'
            if detail['mapped_name']:
                mapped_target_text = 'yes' if detail['mapped_in_custom_taxonomy'] else 'no'

            self.stdout.write(
                f"  - {name}: status={detail['status']}; TAXA_MAP={mapping_text}; "
                f"custom_taxonomy={custom_text}; mapped_target={mapped_target_text}"
                f"{f'; mapped_name={detail['mapped_name']}' if detail['mapped_name'] else ''}"
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
        url = f'{base_url}/{filename}'
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

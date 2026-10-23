import json
import os
import zipfile

from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings, TEST_MEDIA_ROOT
from app_kit.tests.mixins import WithUser, WithTenantClient, WithMedia, WithImageStore

from app_kit.features.nature_guides.tests.common import WithNatureGuide, WithMatrixFilters
from app_kit.features.nature_guides.models import (
    NatureGuide, NatureGuidesTaxonTree, MetaNode,
    MatrixFilter, NodeFilterSpace, NatureGuideCrosslinks,
)
from app_kit.taxonomy.utils import NuidManager


class TestExportImportNatureGuide(
    WithMatrixFilters, WithNatureGuide, WithImageStore, WithMedia,
    WithUser, WithTenantClient, TenantTestCase,
):

    def setUp(self):
        super().setUp()
        self._build_source_guide()

    def _build_source_guide(self):
        self.source_guide = self.create_nature_guide('Source Guide')
        self.start_node = NatureGuidesTaxonTree.objects.get(
            nature_guide=self.source_guide,
            meta_node__node_type='root',
        )
        self.node_a = self.create_node(self.start_node, 'Node A')
        self.node_b = self.create_node(self.start_node, 'Node B')
        self.child_node = self.create_node(self.node_a, 'Child Node', node_type='result')

        NatureGuideCrosslinks.objects.create(
            parent=self.node_a,
            child=self.node_b,
        )

        self.create_all_matrix_filters(self.node_a)
        self.fill_matrix_filters_nodes(self.node_a, [self.node_b])

    def _delete_guide(self, guide):
        # TaxonTree.parent is PROTECT; null it out so cascade deletion works.
        NatureGuidesTaxonTree.objects.filter(nature_guide=guide).update(parent=None)
        guide.delete()

    def _zip_path(self):
        schema = self.tenant.schema_name
        safe_name = self.source_guide.name.replace(' ', '_')
        return os.path.join(
            TEST_MEDIA_ROOT, 'nature_guides_exports', schema,
            f'nature_guide_{self.source_guide.pk}_{safe_name}.zip',
        )

    def _export_source(self):
        call_command(
            'export_nature_guide',
            self.tenant.schema_name,
            self.source_guide.pk,
            verbosity=0,
        )
        return self._zip_path()

    # ------------------------------------------------------------------
    # Helpers to count source guide objects (captured before deletion)
    # ------------------------------------------------------------------

    def _source_counts(self):
        ng_pk = self.source_guide.pk
        return {
            'nodes': NatureGuidesTaxonTree.objects.filter(nature_guide=ng_pk).count(),
            'meta_nodes': MetaNode.objects.filter(nature_guide=ng_pk).count(),
            'filters': MatrixFilter.objects.filter(meta_node__nature_guide=ng_pk).count(),
            'node_filter_spaces': NodeFilterSpace.objects.filter(
                node__nature_guide=ng_pk
            ).count(),
            'crosslinks': NatureGuideCrosslinks.objects.filter(
                parent__nature_guide=ng_pk
            ).count(),
        }

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    @test_settings
    def test_export_creates_zip(self):
        zip_path = self._export_source()
        self.assertTrue(os.path.exists(zip_path))

    @test_settings
    def test_export_zip_contains_required_files(self):
        zip_path = self._export_source()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
        self.assertIn('nature_guide_data.json', names)
        self.assertIn('manifest.json', names)

    @test_settings
    def test_export_manifest_has_correct_metadata(self):
        zip_path = self._export_source()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            manifest = json.loads(zf.read('manifest.json'))
        self.assertEqual(manifest['source_schema'], self.tenant.schema_name)
        self.assertEqual(manifest['nature_guide_id'], self.source_guide.pk)
        self.assertEqual(manifest['nature_guide_name'], self.source_guide.name)

    @test_settings
    def test_export_fixture_contains_all_model_types(self):
        zip_path = self._export_source()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            data = json.loads(zf.read('nature_guide_data.json'))
        model_labels = {obj['model'] for obj in data}
        for expected in (
            'nature_guides.natureguide',
            'nature_guides.metanode',
            'nature_guides.natureguidestaxontree',
            'nature_guides.natureguidecrosslinks',
            'nature_guides.matrixfilter',
            'nature_guides.matrixfilterspace',
            'nature_guides.nodefilterspace',
        ):
            self.assertIn(expected, model_labels)

    @test_settings
    def test_export_fixture_contains_only_this_guide(self):
        """Objects from an unrelated second guide must not appear in the export."""
        other_guide = self.create_nature_guide('Other Guide')
        zip_path = self._export_source()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            data = json.loads(zf.read('nature_guide_data.json'))
        ng_entries = [o for o in data if o['model'] == 'nature_guides.natureguide']
        self.assertEqual(len(ng_entries), 1)
        self.assertEqual(ng_entries[0]['pk'], self.source_guide.pk)

    @test_settings
    def test_import_creates_new_guide(self):
        source_counts = self._source_counts()
        zip_path = self._export_source()

        # Delete source so its UUIDs don't conflict on import into the same schema.
        self._delete_guide(self.source_guide)
        # Add an unrelated guide to occupy PKs and force offset remapping.
        self.create_nature_guide('Existing Guide')

        ng_count_before = NatureGuide.objects.count()
        node_count_before = NatureGuidesTaxonTree.objects.count()
        meta_node_count_before = MetaNode.objects.count()
        filter_count_before = MatrixFilter.objects.count()

        call_command('import_nature_guide', self.tenant.schema_name, zip_path, verbosity=0)

        self.assertEqual(NatureGuide.objects.count(), ng_count_before + 1)
        self.assertEqual(
            NatureGuidesTaxonTree.objects.count(),
            node_count_before + source_counts['nodes'],
        )
        self.assertEqual(
            MetaNode.objects.count(),
            meta_node_count_before + source_counts['meta_nodes'],
        )
        self.assertEqual(
            MatrixFilter.objects.count(),
            filter_count_before + source_counts['filters'],
        )

    @test_settings
    def test_import_remaps_nuids(self):
        zip_path = self._export_source()
        old_pk = self.source_guide.pk

        self._delete_guide(self.source_guide)
        existing_guide = self.create_nature_guide('Existing Guide')

        max_ng_pk = NatureGuide.objects.order_by('-pk').first().pk
        expected_imported_pk = old_pk + max_ng_pk

        call_command('import_nature_guide', self.tenant.schema_name, zip_path, verbosity=0)

        imported_guide = NatureGuide.objects.get(pk=expected_imported_pk)

        nuid_mgr = NuidManager()
        expected_prefix = nuid_mgr.decimal_to_nuid(expected_imported_pk)

        for node in NatureGuidesTaxonTree.objects.filter(nature_guide=imported_guide):
            self.assertTrue(
                node.taxon_nuid.startswith(expected_prefix),
                f'{node.taxon_nuid!r} does not start with {expected_prefix!r}',
            )
            self.assertTrue(node.source_id.startswith(expected_prefix))

    @test_settings
    def test_import_preserves_node_names(self):
        source_node_names = set(
            NatureGuidesTaxonTree.objects.filter(nature_guide=self.source_guide)
            .values_list('meta_node__name', flat=True)
        )
        zip_path = self._export_source()
        self._delete_guide(self.source_guide)
        self.create_nature_guide('Existing Guide')

        call_command('import_nature_guide', self.tenant.schema_name, zip_path, verbosity=0)

        imported_guide = NatureGuide.objects.filter(name='Source Guide').first()
        self.assertIsNotNone(imported_guide)

        imported_node_names = set(
            NatureGuidesTaxonTree.objects.filter(nature_guide=imported_guide)
            .values_list('meta_node__name', flat=True)
        )
        self.assertEqual(source_node_names, imported_node_names)

    @test_settings
    def test_import_preserves_matrix_filter_names(self):
        source_filter_names = set(
            MatrixFilter.objects.filter(meta_node__nature_guide=self.source_guide)
            .values_list('name', flat=True)
        )
        zip_path = self._export_source()
        self._delete_guide(self.source_guide)
        self.create_nature_guide('Existing Guide')

        call_command('import_nature_guide', self.tenant.schema_name, zip_path, verbosity=0)

        imported_guide = NatureGuide.objects.filter(name='Source Guide').first()
        imported_filter_names = set(
            MatrixFilter.objects.filter(meta_node__nature_guide=imported_guide)
            .values_list('name', flat=True)
        )
        self.assertEqual(source_filter_names, imported_filter_names)

    @test_settings
    def test_import_preserves_crosslinks(self):
        source_crosslink_count = NatureGuideCrosslinks.objects.filter(
            parent__nature_guide=self.source_guide
        ).count()
        zip_path = self._export_source()
        self._delete_guide(self.source_guide)
        self.create_nature_guide('Existing Guide')

        call_command('import_nature_guide', self.tenant.schema_name, zip_path, verbosity=0)

        imported_guide = NatureGuide.objects.filter(name='Source Guide').first()
        imported_crosslink_count = NatureGuideCrosslinks.objects.filter(
            parent__nature_guide=imported_guide
        ).count()
        self.assertEqual(source_crosslink_count, imported_crosslink_count)

    @test_settings
    def test_import_slug_deduplication(self):
        """Slugs are deduplicated when the same node names already exist in the target schema."""
        zip_path = self._export_source()
        self._delete_guide(self.source_guide)

        # Create a second guide whose nodes share names with the source guide,
        # so their slugs will collide during import.
        guide_x = self.create_nature_guide('Guide X')
        start_x = NatureGuidesTaxonTree.objects.get(
            nature_guide=guide_x, meta_node__node_type='root',
        )
        self.create_node(start_x, 'Node A')
        self.create_node(start_x, 'Node B')

        call_command('import_nature_guide', self.tenant.schema_name, zip_path, verbosity=0)

        # All slugs must be unique.
        all_slugs = list(
            NatureGuidesTaxonTree.objects.values_list('slug', flat=True).exclude(slug__isnull=True)
        )
        self.assertEqual(len(all_slugs), len(set(all_slugs)))

        # The imported guide and guide_x must not share any slugs.
        imported_guide = NatureGuide.objects.filter(name='Source Guide').first()
        imported_slugs = set(
            NatureGuidesTaxonTree.objects.filter(nature_guide=imported_guide)
            .values_list('slug', flat=True)
            .exclude(slug__isnull=True)
        )
        guide_x_slugs = set(
            NatureGuidesTaxonTree.objects.filter(nature_guide=guide_x)
            .values_list('slug', flat=True)
            .exclude(slug__isnull=True)
        )
        self.assertFalse(imported_slugs & guide_x_slugs)

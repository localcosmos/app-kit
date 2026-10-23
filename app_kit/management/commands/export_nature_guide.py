import os
import json
import zipfile
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.core import serializers
from django_tenants.utils import schema_context

from app_kit.features.nature_guides.models import (
    NatureGuide, MetaNode, NatureGuidesTaxonTree, NatureGuideCrosslinks,
    MatrixFilterSpace, NatureGuidesTaxonSynonym, NatureGuidesTaxonLocale,
    MatrixFilter, NodeFilterSpace, MatrixFilterRestriction,
)
from app_kit.models import ContentImage, ImageStore


class Command(BaseCommand):
    help = 'Export a single Nature Guide as a ZIP file from a specific tenant schema'

    def add_arguments(self, parser):
        parser.add_argument(
            'schema_name',
            type=str,
            help='The tenant schema name to export from.',
        )
        parser.add_argument(
            'nature_guide_id',
            type=int,
            help='The primary key of the NatureGuide to export.',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default=None,
            help='Directory to write the ZIP file to (defaults to MEDIA_ROOT/nature_guides_exports/<schema>).',
        )

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        ng_id = options['nature_guide_id']

        with schema_context(schema_name):
            try:
                nature_guide = NatureGuide.objects.get(pk=ng_id)
            except NatureGuide.DoesNotExist:
                raise CommandError(
                    f'NatureGuide with id {ng_id} not found in schema "{schema_name}"'
                )

            output_dir = options['output_dir'] or os.path.join(
                settings.MEDIA_ROOT, 'nature_guides_exports', schema_name
            )
            os.makedirs(output_dir, exist_ok=True)

            # --- Collect all related querysets ---
            meta_nodes = MetaNode.objects.filter(nature_guide=nature_guide)
            meta_node_ids = list(meta_nodes.values_list('pk', flat=True))

            tree_nodes = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide)
            tree_node_ids = list(tree_nodes.values_list('pk', flat=True))

            crosslinks = NatureGuideCrosslinks.objects.filter(
                parent__nature_guide=nature_guide
            )

            matrix_filters = MatrixFilter.objects.filter(meta_node__in=meta_nodes)
            matrix_filter_ids = list(matrix_filters.values_list('pk', flat=True))

            matrix_filter_spaces = MatrixFilterSpace.objects.filter(
                matrix_filter__in=matrix_filters
            )
            matrix_filter_space_ids = list(matrix_filter_spaces.values_list('pk', flat=True))

            node_filter_spaces = NodeFilterSpace.objects.filter(node__in=tree_nodes)

            matrix_filter_restrictions = MatrixFilterRestriction.objects.filter(
                restricted_matrix_filter__in=matrix_filters
            )

            taxon_synonyms = NatureGuidesTaxonSynonym.objects.filter(taxon__in=tree_nodes)
            taxon_locales = NatureGuidesTaxonLocale.objects.filter(taxon__in=tree_nodes)

            # --- Collect ContentImages for this nature guide's objects only ---
            ng_ct = ContentType.objects.get_for_model(NatureGuide)
            meta_node_ct = ContentType.objects.get_for_model(MetaNode)
            tree_node_ct = ContentType.objects.get_for_model(NatureGuidesTaxonTree)
            mfs_ct = ContentType.objects.get_for_model(MatrixFilterSpace)

            content_images = ContentImage.objects.filter(
                Q(content_type=ng_ct, object_id=nature_guide.pk)
                | Q(content_type=meta_node_ct, object_id__in=meta_node_ids)
                | Q(content_type=tree_node_ct, object_id__in=tree_node_ids)
                | Q(content_type=mfs_ct, object_id__in=matrix_filter_space_ids)
            )

            image_store_ids = list(
                content_images.values_list('image_store_id', flat=True).distinct()
            )
            image_stores = ImageStore.objects.filter(pk__in=image_store_ids)

            # --- Serialize ---
            all_objects = (
                [nature_guide]
                + list(meta_nodes)
                + list(tree_nodes)
                + list(crosslinks)
                + list(matrix_filters)
                + list(matrix_filter_spaces)
                + list(node_filter_spaces)
                + list(matrix_filter_restrictions)
                + list(taxon_synonyms)
                + list(taxon_locales)
                + list(image_stores)
                + list(content_images)
            )

            json_data = serializers.serialize(
                'json',
                all_objects,
                indent=2,
                use_natural_foreign_keys=True,
            )

            # --- Manifest ---
            manifest = {
                'source_schema': schema_name,
                'nature_guide_id': ng_id,
                'nature_guide_name': nature_guide.name,
            }

            # --- Build ZIP ---
            safe_name = (nature_guide.name or str(ng_id)).replace(' ', '_')
            zip_filename = os.path.join(
                output_dir, f'nature_guide_{ng_id}_{safe_name}.zip'
            )

            with zipfile.ZipFile(zip_filename, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('nature_guide_data.json', json_data)
                zf.writestr('manifest.json', json.dumps(manifest, indent=2))

                for istore in image_stores:
                    if istore.source_image:
                        filepath = istore.source_image.path
                        if os.path.exists(filepath):
                            arcname = os.path.relpath(filepath, settings.MEDIA_ROOT)
                            zf.write(filepath, arcname)
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'Image file not found: {filepath}')
                            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Exported NatureGuide "{nature_guide.name}" (id={ng_id}) '
                    f'from schema "{schema_name}" to:\n  {zip_filename}'
                )
            )

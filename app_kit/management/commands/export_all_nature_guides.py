import os
import zipfile
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django_tenants.utils import schema_context  # Assuming django-tenants for multi-tenancy
from django.core import serializers

from app_kit.features.nature_guides.models import (NatureGuide, MetaNode, NatureGuidesTaxonTree, NatureGuideCrosslinks, MatrixFilterSpace,
                                                   NatureGuidesTaxonSynonym, NatureGuidesTaxonLocale, MatrixFilter, NodeFilterSpace,
                                                   MatrixFilterRestriction)

from app_kit.models import ContentImage, ImageStore


class Command(BaseCommand):
    help = 'Export all Nature Guides as ZIP files for a specific tenant schema'

    def add_arguments(self, parser):
        parser.add_argument(
            'schema_name',
            type=str,
            help='The tenant schema name to export Nature Guides from (required).',
        )

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        
        # Use schema_context to switch to the tenant's schema
        with schema_context(schema_name):
            export_path = os.path.join(settings.MEDIA_ROOT, 'nature_guides_exports', schema_name)
            os.makedirs(export_path, exist_ok=True)
            
            nature_guide_content_type = ContentType.objects.get_for_model(NatureGuide)
            meta_node_content_type = ContentType.objects.get_for_model(MetaNode)
            taxon_tree_content_type = ContentType.objects.get_for_model(NatureGuidesTaxonTree)
            matrix_filter_space_content_type = ContentType.objects.get_for_model(MatrixFilterSpace)
            
            image_content_types = [nature_guide_content_type, meta_node_content_type,
                                   taxon_tree_content_type, matrix_filter_space_content_type]
            
            content_images = ContentImage.objects.filter(
                content_type__in=image_content_types
            )
            
            # get all full filepaths of those images
            image_filepaths = []
            for ci in content_images:
                if ci.image_store and ci.image_store.source_image:
                    image_filepaths.append(ci.image_store.source_image.path)
            
            # zip all those images into a single zip file
            zip_filename = os.path.join(export_path, f'nature_guides_images_{schema_name}.zip')
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for filepath in image_filepaths:
                    arcname = os.path.relpath(filepath, settings.MEDIA_ROOT)
                    zipf.write(filepath, arcname)
            
            # Collect all objects to export
            all_objects = []
            nature_guide_models = [NatureGuide, MetaNode, NatureGuidesTaxonTree, NatureGuideCrosslinks, MatrixFilterSpace,
                                   NatureGuidesTaxonSynonym, NatureGuidesTaxonLocale, MatrixFilter, NodeFilterSpace,
                                   MatrixFilterRestriction]
            for model in nature_guide_models:
                all_objects.extend(model.objects.all())
            all_objects.extend(content_images)  # The filtered ContentImage instances
            
            # Collect related ImageStore instances
            image_stores = [ci.image_store for ci in content_images if ci.image_store]
            all_objects.extend(image_stores)
            
            # Serialize to JSON
            data_filename = os.path.join(export_path, 'nature_guides_data.json')
            with open(data_filename, 'w') as f:
                serializers.serialize('json', all_objects, stream=f)
            
            # Add the data file to the ZIP
            with zipfile.ZipFile(zip_filename, 'a') as zipf:
                zipf.write(data_filename, 'nature_guides_data.json')
            
            # Optionally, remove the temporary data file after adding to ZIP
            os.remove(data_filename)
            
            self.stdout.write(f'All Nature Guides exported to: {export_path}')

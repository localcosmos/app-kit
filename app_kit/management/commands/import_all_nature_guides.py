import os
import zipfile
import tempfile
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django_tenants.utils import schema_context
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Import all Nature Guides from a ZIP file for a specific tenant schema'

    def add_arguments(self, parser):
        parser.add_argument(
            'schema_name',
            type=str,
            help='The tenant schema name to import Nature Guides into (required).',
        )
        parser.add_argument(
            '--zip-path',
            type=str,
            help='Path to the ZIP file to import (optional, defaults to the export path).',
        )

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        zip_path = options.get('zip_path')
        
        if not zip_path:
            export_path = os.path.join(settings.MEDIA_ROOT, 'nature_guides_exports', schema_name)
            zip_path = os.path.join(export_path, f'nature_guides_images_{schema_name}.zip')
        
        if not os.path.exists(zip_path):
            raise CommandError(f'ZIP file not found: {zip_path}')
        
        # Use schema_context to switch to the tenant's schema
        with schema_context(schema_name):
            # Create a temporary directory to extract files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract the ZIP file
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # Find the data JSON file
                data_filename = os.path.join(temp_dir, 'nature_guides_data.json')
                if not os.path.exists(data_filename):
                    raise CommandError('nature_guides_data.json not found in ZIP')
                
                # Load the data using loaddata
                call_command('loaddata', data_filename, verbosity=1)
                
                # Extract images to MEDIA_ROOT
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')):  # Add more extensions if needed
                            src_path = os.path.join(root, file)
                            # Calculate the relative path from temp_dir
                            rel_path = os.path.relpath(src_path, temp_dir)
                            dest_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            # Move or copy the file
                            os.rename(src_path, dest_path)  # Use shutil.move if needed
            
            self.stdout.write(f'All Nature Guides imported successfully for schema: {schema_name}')
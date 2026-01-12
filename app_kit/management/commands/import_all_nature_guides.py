import os
import zipfile
import tempfile
import shutil
import json  # Add this import
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
        parser.add_argument(
            '--source-schema',
            type=str,
            default='treesofbavaria',
            help='The source schema name in the ZIP (defaults to "treesofbavaria").',
        )

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        zip_path = options.get('zip_path')
        source_schema = options['source_schema']
        
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
                
                # Modify and load the data JSON file
                data_filename = os.path.join(temp_dir, 'nature_guides_data.json')
                if not os.path.exists(data_filename):
                    raise CommandError('nature_guides_data.json not found in ZIP')
                
                # Load, modify, and save the JSON
                with open(data_filename, 'r') as f:
                    data = json.load(f)
                
                # Replace source_schema with schema_name in string fields (e.g., image paths)
                def replace_schema(obj):
                    if isinstance(obj, str):
                        return obj.replace(source_schema, schema_name)
                    elif isinstance(obj, dict):
                        return {k: replace_schema(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [replace_schema(item) for item in obj]
                    return obj
                
                modified_data = replace_schema(data)
                
                with open(data_filename, 'w') as f:
                    json.dump(modified_data, f)
                
                # Load the modified data using loaddata
                call_command('loaddata', data_filename, verbosity=1)
                
                # Extract and move images to MEDIA_ROOT, replacing schema in paths
                moved_count = 0
                skipped_count = 0
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, temp_dir)
                        # Only process files under the source schema's imagestore (to avoid copying unrelated files)
                        if rel_path.startswith(f'{source_schema}/imagestore/'):
                            # Replace source_schema with schema_name in rel_path
                            rel_path = rel_path.replace(source_schema, schema_name, 1)
                            dest_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            # Move the file regardless of extension (since ImageStore may have various files)
                            shutil.move(src_path, dest_path)
                            moved_count += 1
                            self.stdout.write(f'Moved: {src_path} -> {dest_path}')
                        else:
                            skipped_count += 1
                            self.stdout.write(f'Skipped (not in imagestore): {rel_path}')

                self.stdout.write(f'Moved {moved_count} files, skipped {skipped_count} files.')

            self.stdout.write(f'All Nature Guides imported successfully for schema: {schema_name}')
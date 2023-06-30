from django.core.management.base import BaseCommand, CommandError

from app_kit.models import MetaApp, MetaAppGenericContent

from app_kit.features.frontend.models import Frontend
from django.contrib.contenttypes.models import ContentType

from django.conf import settings

import os, sys

'''
    Migrate all apps to the new frontend layout
    create an app in the languages english, german and japanese (testing characters)
'''
class Command(BaseCommand):
    
    help = 'Migrate apps to frontend feature'


    def _create_frontend(self, meta_app):

        frontend_content_type = ContentType.objects.get_for_model(Frontend)

        frontend_exists = MetaAppGenericContent.objects.filter(meta_app = meta_app,
            content_type = frontend_content_type).exists()

        if not frontend_exists:
        
            feature_name = str(Frontend._meta.verbose_name)
            feature = Frontend.objects.create(feature_name, meta_app.primary_language)


            link = MetaAppGenericContent(
                meta_app = meta_app,
                content_type = frontend_content_type,
                object_id = feature.id,
            )
            link.save()


    def handle(self, *args, **options):

        meta_apps = MetaApp.objects.all()

        for meta_app in meta_apps:

            # Step 1: add the Frontend feature
            self.stdout.write('Creating frontend feature for {0}.'.format(meta_app.name))
            self._create_frontend(meta_app)

            # Step 2: rename the current app folder in /opt/apps to not lose any data
            app_release_builder = meta_app.get_release_builder()

            app_root = app_release_builder._app_root_path

            if os.path.isdir(app_root):
                self.stdout.write('Found existing app at {0}'.format(app_root))

            new_folder_name = '{0}_old'.format(str(meta_app.uuid))
            new_app_root = os.path.join(settings.APP_KIT_ROOT, new_folder_name)

            if os.path.isdir(new_app_root):
                self.stdout.write('{0} already exists'.format(new_app_root))
            else:
                self.stdout.write('Moving {0} -> {1}'.format(app_root, new_app_root))

                os.rename(app_root, new_app_root)

            if os.path.isdir(app_root):
                self.stdout.write('old app directory {1} STILL  exists. Aborting.'.format(app_root))
                sys.exit(1)

            else:

                # Step 3: recreate the app version on disk
                self.stdout.write('Creating app version {0} for {1}.'.format(meta_app.current_version, meta_app.name))
                app_builder = meta_app.get_app_builder()
                app_builder.create_app_version()
                self.stdout.write('Finished creating app version {0} build for {1}.'.format(meta_app.current_version,
                                                                                        meta_app.name))

                # Step 4: recreate preview
                self.stdout.write('Creating preview version for {0}.'.format(meta_app.name))
                preview_builder = meta_app.get_preview_builder()
                preview_builder.build()

                self.stdout.write('Finished creating preview build for {0}.'.format(meta_app.name))

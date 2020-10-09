from django.conf import settings
from django.db import connection, models
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.apps import apps
from django.urls import reverse

from django.contrib.contenttypes.fields import GenericRelation

from collections import OrderedDict

import os, json, hashlib, time, shutil

from localcosmos_server.slugifier import create_unique_slug
from django.template.defaultfilters import slugify # package_name

from .generic import GenericContentMethodsMixin

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy
from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon, LazyTaxonList

from .utils import import_module

from .generic_content_validation import ValidationError, ValidationWarning

from content_licencing.models import ContentLicenceRegistry

from django_tenants.utils import get_tenant_model, get_tenant_domain_model

from app_kit.app_kit_api.models import AppKitJobs

from localcosmos_server.models import App, SecondaryAppLanguages

from datetime import datetime
from PIL import Image


'''--------------------------------------------------------------------------------------------------------------
    MIXINS
--------------------------------------------------------------------------------------------------------------'''
class ContentImageMixin:

    def _content_images(self, image_type='image'):

        content_type = ContentType.objects.get_for_model(self.__class__)
        self.content_images = ContentImage.objects.filter(content_type=content_type, object_id=self.pk,
                                                          image_type=image_type)

        return self.content_images

    def images(self, image_type='image'):
        return self._content_images(image_type=image_type)

    def image(self, image_type='image'):
        content_image = self._content_images(image_type=image_type).first()

        if content_image:
            return content_image

        return None

    def image_url(self, size=400):

        content_image = self.image()

        if content_image:
            return content_image.image_url(size)

        return static('noimage.png')


    # this also deletes ImageStore entries and images on disk
    def delete_images(self):
        content_type = ContentType.objects.get_for_model(self.__class__)
        content_images = ContentImage.objects.filter(content_type=content_type, object_id=self.pk)

        for image in content_images:
            # delete model db entries
            image.image_store.delete()
            image.delete()
        
'''
    Scenario:
    - user uploads image with taxon
    - the user changes the taxon of the associated content
    -> the associated image taxon should be altered, too
'''
class UpdateContentImageTaxonMixin:

    def get_content_image_taxon(self):
        return self.taxon

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        taxon = self.get_content_image_taxon()

        if taxon:
            content_type = ContentType.objects.get_for_model(self)
            content_images = ContentImage.objects.filter(content_type=content_type, object_id=self.pk)
            
            for content_image in content_images:
                image = content_image.image_store
                if image.taxon and image.taxon.taxon_source == taxon.taxon_source and image.taxon.taxon_latname == taxon.taxon_latname and image.taxon.taxon_author == taxon.taxon_author:
                    continue

                image.set_taxon(taxon)
                image.save()
                

'''--------------------------------------------------------------------------------------------------------------
    APP
--------------------------------------------------------------------------------------------------------------'''

APP_BUILD_STATUS = (
    ('failing', _('failing')), # build failed, see log files
    ('passing', _('passing')), # build passed, packages have been built and are present
    ('in_progress', _('build in progress')), # build is in progress, async
)

APP_VALIDATION_STATUS = (
    ('in_progress', _('validation in progress')),
    ('valid', _('valid')),
    ('warnings', _('warnings')),
    ('errors', _('errors')),
)


from .appbuilders import (get_available_appbuilder_versions, get_latest_app_preview_builder,
                          get_app_preview_builder_class, get_app_release_builder_class)

INSTALLED_APPBUILDER_VERSIONS = [(version, version) for version in get_available_appbuilder_versions()]

'''
    used to create new apps
    - one subdomain per app on LC
'''
class MetaAppManager(models.Manager):


    def _create_required_features(self, app_preview_builder, meta_app):
        # create all required features and link them to the app
        for required_feature in app_preview_builder.required_features:
            
            feature_module = import_module(required_feature)
            FeatureModel = feature_module.models.FeatureModel
            
            feature_name = str(FeatureModel._meta.verbose_name)
            feature = FeatureModel.objects.create(feature_name, meta_app.primary_language)

            link = MetaAppGenericContent(
                meta_app = meta_app,
                content_type = ContentType.objects.get_for_model(feature),
                object_id = feature.id,
            )
            link.save()


    def create(self, name, primary_language, domain_name, tenant, subdomain, **kwargs):

        appbuilder_version = kwargs.pop('appbuilder_version', None)
        secondary_languages = kwargs.pop('secondary_languages', [])
        global_options = kwargs.pop('global_options', {})

        # get an AppPreviewBuilder instance
        if appbuilder_version is None:
            app_preview_builder = get_latest_app_preview_builder()
            appbuilder_version = app_preview_builder.version
        else:
            AppPreviewBuilderClass = get_app_preview_builder_class(appbuilder_version)
            app_preview_builder = AppPreviewBuilderClass()
            appbuilder_version = app_preview_builder.version

        package_name_base = 'org.localcosmos.{0}'.format(slugify(name).replace('-','').lower()[:30])
        package_name = package_name_base

        # make sure it is unique
        exists = self.filter(package_name=package_name).exists()
        i = 2
        while exists: 
            package_name = '{0}{1}'.format(package_name_base, i)
            i += 1
            exists = self.filter(package_name=package_name).exists()

        if 'theme' in kwargs:
            theme = kwargs['theme']
        else:
            theme = app_preview_builder.default_app_theme

        # this also creates the online content link
        extra_app_kwargs = {}
        if 'uuid' in kwargs:
           extra_app_kwargs['uuid'] = kwargs['uuid']
        app = App.objects.create(name, primary_language, subdomain, **extra_app_kwargs)

        Domain = get_tenant_domain_model()

        # 2 cases: domain exists as an empty app kit (app_id = None) or does not exist at all

        domain = Domain.objects.filter(tenant=tenant, domain=domain_name, app__isnull=True).first()

        if not domain:
            
            is_primary_domain = Domain.objects.filter(tenant=tenant, is_primary=True).exists() == False

            domain = Domain(
                tenant=tenant,
                domain=domain_name,
                is_primary=is_primary_domain,
            )

        domain.app=app
        domain.save()

        # create app and profile
        meta_app = self.model(
            app=app,
            appbuilder_version=str(appbuilder_version),
            theme=theme,
            package_name=package_name,
            global_options=global_options
        )

        meta_app.save()

        # add all languages
        for language_code in secondary_languages:
            if language_code != primary_language:

                # create the new locale
                secondary_language = SecondaryAppLanguages(
                    app=app,
                    language_code=language_code,
                )
                secondary_language.save()

        self._create_required_features(app_preview_builder, meta_app)

        meta_app.create_version(meta_app.current_version)
        
        return meta_app

'''
    META APP
    - uuid, primary_language and name lie in MetaApp.app
    - published versions cannot be changed
    - if the appbuilder version has been changed the cordova project has to be recreated
    - for the end user, the cordova create process is irrelevant
    - the appbuilder version is strictly bound to the app version
'''
class MetaApp(ContentImageMixin, GenericContentMethodsMixin, models.Model):

    app = models.OneToOneField(App, on_delete=models.CASCADE)

    @property
    def uuid(self):
        return self.app.uuid

    @property
    def name(self):
        return self.app.name

    @property
    def primary_language(self):
        return self.app.primary_language
    
    published_version = models.IntegerField(null=True)
    current_version = models.IntegerField(default=1)
    is_locked = models.BooleanField(default=False)
    global_options = models.JSONField(null=True)

    package_name = models.CharField(max_length=100, unique=True) #app identifier: localcosmos.package_name

    build_settings = models.JSONField(null=True)

    # version_specific build number
    build_number = models.IntegerField(null=True)

    # the theme name of the app
    # this has to be a required field, without a theme, eg user content preview does not work
    theme = models.CharField(max_length=255)

    # links to several stores, using json for future safety
    store_links = models.JSONField(null=True)

    # appbuilder is not changeable by user
    appbuilder_version = models.CharField(max_length=10, choices=INSTALLED_APPBUILDER_VERSIONS)
    
    build_status = models.CharField(max_length=50, choices=APP_BUILD_STATUS, null=True)
    last_build_report = models.JSONField(null=True)

    validation_status = models.CharField(max_length=50, choices=APP_VALIDATION_STATUS, null=True)
    last_validation_report = models.JSONField(null=True)

    last_release_report = models.JSONField(null=True)

    last_modified_at = models.DateTimeField(auto_now=True)
    last_published_at = models.DateTimeField(null=True)

    objects = MetaAppManager()

    _backbone = None


    @property
    def domain(self):
        Domain = get_tenant_domain_model()
        domain = Domain.objects.get(app=self.app)
        return domain.domain

    @property
    def tenant(self):
        Tenant = get_tenant_model()
        return Tenant.objects.get(schema_name=connection.schema_name)

    # the global build status includes build processes on other machines, like a mac, which are tracked
    # by the model AppKitJobs
    # in_progress, passing, failing or None
    @property
    def global_build_status(self):
        

        build_jobs = AppKitJobs.objects.filter(meta_app_uuid=self.uuid, job_type='build')

        in_progress_jobs = build_jobs.filter(finished_at__isnull=True)

        if self.build_status == 'in_progress' or in_progress_jobs.exists():
            return 'in_progress'
        
        # the build is not in progress
        # passing requires all jobs passing for the current version
        elif self.build_status == 'passing':
            # finished jobs can have either failed or success as job_result
            failed_jobs = build_jobs.filter(finished_at__isnull=False, app_version=self.current_version,
                                            job_result__success=False)

            if not failed_jobs.exists():
                return 'passing'

            else:
                return 'failing'

        elif self.build_status == 'failing':
            return 'failing'

        return None


    @property
    def full_url(self):
        content_type = ContentType.objects.get_for_model(self)
        url_kwargs = {
            'meta_app_id' : self.pk,
            'content_type_id' : content_type.id,
            'object_id' : self.pk,
        }
        
        view_url = reverse('manage_metaapp', kwargs=url_kwargs, urlconf=settings.ROOT_URLCONF)

        url = '{0}{1}'.format(self.domain, view_url)
        
        return url

    def languages(self):
        return self.app.languages()
    
    def secondary_languages(self):
        return self.app.secondary_languages()

    # theme
    # meta_app.get_theme always uses the apps preview theme
    def get_theme(self):
        app_preview_builder = self.get_preview_builder()
        return app_preview_builder.get_theme(self.theme)

    
    def get_preview_builder(self):
        AppPreviewBuilderClass = get_app_preview_builder_class(self.appbuilder_version)
        return AppPreviewBuilderClass()

    def get_release_builder(self):
        AppReleaseBuilderClass = get_app_release_builder_class(self.appbuilder_version)
        return AppReleaseBuilderClass()

    
    # BUILDING 
    # on a new version, the old www folder is moved and renamed, same for config.xml
    # if a new appbuilder version is chosen, the create command has to be rerun
    # kwargs can be:
    # app_version: version of the app to build
    # appbuilder_version: version of the appbuilder to use
    # force_recreate_cordova: force the builder to recreate the cordova project
    def lock_generic_contents(self):
        contents = MetaAppGenericContent.objects.filter(meta_app=self)
        for link in contents:
            link.generic_content.is_locked = True
            link.generic_content.save()


    def unlock_generic_contents(self):
        contents = MetaAppGenericContent.objects.filter(meta_app=self)
        for link in contents:
            link.generic_content.is_locked = False
            link.generic_content.save()


    def get_primary_localization(self):
        locale = {}

        locale[self.name] = self.name

        # add the theme specific texts
        theme = self.get_theme()
        theme_text_types = theme.user_content['texts']

        app_preview_builder = self.get_preview_builder()
        primary_locale = app_preview_builder.get_primary_locale(self)

        if primary_locale:
            
            for key, definition in theme_text_types.items():

                if key in primary_locale:

                    text = primary_locale[key]
                    if text and len(text) > 0:
                        locale[key] = text
                    else:
                        locale[key] = ''
        
        return locale

    
    # all uploads for an app (except "design and text") go to this folder
    def media_path(self):
        path = '/'.join(['apps', str(self.uuid)])
        return path


    def features(self):
        return MetaAppGenericContent.objects.filter(meta_app=self)
    

    def addable_features(self):
        appbuilder = self.get_preview_builder()

        features = []

        for feature in appbuilder.feature_choices():
            features.append(feature['feature_model'])

        return features
    

    def get_generic_content_link(self, generic_content):
        link = MetaAppGenericContent.objects.filter(
            meta_app=self,
            content_type=ContentType.objects.get_for_model(generic_content),
            object_id=generic_content.id
        ).first()

        return link

    # TAXONOMY
    def backbone(self):
        if self._backbone is None:
            link = MetaAppGenericContent.objects.get(meta_app=self,
                        content_type=ContentType.objects.get_for_model(BackboneTaxonomy))
            self._backbone = link.generic_content
        return self._backbone

    
    def _get_source_nuid_map(self, taxonlist):

        source_nuid_map = {}

        for taxon in taxonlist:

            if not taxon.taxon_source in source_nuid_map:
                source_nuid_map[taxon.taxon_source] = []

            source_nuid_map[taxon.taxon_source].append(taxon.taxon_nuid)

        return source_nuid_map
        

    def taxon_count(self):

        include_full_tree = self.backbone().get_global_option('include_full_tree')

        if include_full_tree:
            models = TaxonomyModelRouter(include_full_tree)
            return models.TaxonTreeModel.objects.all().count()

        # first, count all non-higher-taxa
        taxonlist = self.taxa()
        taxonlist.filter(taxon_include_descendants=False)

        count = taxonlist.count()
        
        source_nuid_map = self._get_source_nuid_map(self.higher_taxa().taxa())

        for source, nuid_list in source_nuid_map.items():
            
            models = TaxonomyModelRouter(source)

            for nuid in nuid_list:

                count += models.TaxonTreeModel.objects.filter(taxon_nuid__startswith=nuid).count()
        
        return count


    # return a LazyTaxonList instance
    def higher_taxa(self):
        # get a list of all taxa, extract with_descendants
        taxonlist = LazyTaxonList()

        feature_links = MetaAppGenericContent.objects.filter(meta_app=self)

        for link in feature_links:
            generic_content = link.generic_content

            lazy_list = generic_content.higher_taxa()

            for queryset in lazy_list.querysets:
                taxonlist.add(queryset)

        
        return taxonlist
    

    # returns a LazyTaxonList
    # all generic_contents do need a taxa() method, nothing else
    def taxa(self):

        taxonlist = LazyTaxonList()
        
        feature_links = MetaAppGenericContent.objects.filter(meta_app=self)

        for link in feature_links:
            generic_content = link.generic_content

            lazy_list = generic_content.taxa()

            for queryset in lazy_list.querysets:
                taxonlist.add(queryset)

        return taxonlist
        
        
    def name_uuids(self):
        taxa = self.taxa()
        return taxa.uuids()


    def has_taxon(self, lazy_taxon):

        # first, check if it is covered by higher taxa
        # returns a LazyTaxonList
        higher_taxonlist = self.higher_taxa()

        exists = higher_taxonlist.included_in_descendants(lazy_taxon)

        if exists:
            return True

        # second, check if it is covered by taxa
        taxonlist = self.taxa()

        return taxonlist.included_in_taxa(lazy_taxon)


    def all_taxa(self):
        include_full_tree = self.backbone().get_global_option('include_full_tree')

        if include_full_tree:
            models = TaxonomyModelRouter(include_full_tree)
            taxa = models.TaxonTreeModel.objects.all().order_by('taxon_latname')
        else:
            taxa = self.taxa()
            
        return taxa
    

    # search the backbone and all associated contents
    def search_taxon(self, searchtext, language='en', limit=10):

        if searchtext == None:
            return []

        searchtext = searchtext.replace('+',' ').strip().upper()
        
        if len(searchtext) < 3:
            return []


        results = []

        # FULL TREE SEARCH
       
        full_tree = self.backbone().get_global_option('include_full_tree')
        
        if full_tree:
            source = full_tree
            models = TaxonomyModelRouter(source)

            query = models.TaxonTreeModel.objects.filter(taxon_latname__istartswith=searchtext)[:limit]

            for taxon in query:

                lazy_taxon = LazyTaxon(instance=taxon)
                result = lazy_taxon.as_typeahead_choice()

                results.append(result)

            if len(results) >= limit:
                return results

            rest_limit = limit - len(results)
            vernacular_query = models.TaxonLocaleModel.objects.filter(language=language,
                                                                      name__icontains=searchtext)[:rest_limit]

            for taxon in vernacular_query:

                label = taxon.name
                lazy_taxon = LazyTaxon(instance=taxon.taxon)
                result = lazy_Taxon.as_typeahead_choice(label=label)

                if result not in results:
                    results.append(result)

            if len(results) >= limit:
                return results

        # FIRST: LATNAMES, direct
        # content.taxa() returns LazyTaxonList
        taxonlist = self.taxa()

        taxonlist.filter(**{'taxon_latname__istartswith':searchtext})

        results += taxonlist.fetch(return_type='typeahead')

        if len(results) >= limit:
            return results
        

        # SECOND: LATNAMES, from higher
        # search each taxonomic source with a uuid restriction
        # the uuid restriction reduces the taxonomic source to the backbone taxa
        rest_limit = limit - len(results)
        
        higher_taxa = self.higher_taxa()

        source_nuid_map = self._get_source_nuid_map(higher_taxa.taxa())

        for source, nuid_list in source_nuid_map.items():

            if len(results) >= limit:
                return results
            
            models = TaxonomyModelRouter(source)

            for nuid in nuid_list:

                if len(results) >= limit:
                    return results

                query = models.TaxonTreeModel.objects.filter(taxon_nuid__startswith=nuid,
                                                             taxon_latname__istartswith=searchtext)[:rest_limit]

                for taxon in query:

                    lazy_taxon = LazyTaxon(instance=taxon)
                    result = lazy_taxon.as_typeahead_choice()

                    if result not in results:
                        results.append(result)

                # NUID BASED VERNAULAR SEARCH
                vernacular_query = models.TaxonLocaleModel.objects.filter(taxon__taxon_nuid__startswith=nuid,
                                            language=language, name__icontains=searchtext)

                for taxon in vernacular_query:

                    label = taxon.name
                    lazy_taxon = LazyTaxon(instance=taxon.taxon)
                    result = lazy_taxon.as_typeahead_choice(label=label)

                    if result not in results:
                        results.append(result)


        if len(results) >= limit:
            return results


        # THIRD : direct vernacular search
        # search all vernacular names using uuid restrictions
        rest_limit = limit - len(results)
        
        taxonlist = self.taxa()
        source_uuids_map = {}

        for taxon in taxonlist:
            if taxon.taxon_source not in source_uuids_map:
                source_uuids_map[taxon.taxon_source] = []
            source_uuids_map[taxon.taxon_source].append(taxon.name_uuid)
            

        for source, uuid_list in source_uuids_map.items():

            if len(results) >= limit:
                return results
            
            models = TaxonomyModelRouter(source)

            query = models.TaxonLocaleModel.objects.filter(taxon__name_uuid__in=uuid_list, language=language,
                                                           name__icontains=searchtext)[:rest_limit]

            for taxon in query:

                label = taxon.name
                lazy_taxon=LazyTaxon(instance=taxon.taxon)
                result = lazy_taxon.as_typeahead_choice(label=label)

                if result not in results:

                    results.append(result)

        return results


    # create app version on disk and set correct preview_version_path
    def create_version(self, app_version):

        if self.current_version > app_version:
            raise ValueError('App versions can only be incremented. Curent version: {0}. You tried to create version {1}'.format(
                self.current_version, app_version))

        elif self.current_version < app_version:
            self.current_version = app_version

        app_preview_builder = self.get_preview_builder()

         # create folders
        app_preview_builder.init_app_version(self, app_version)

        # create preview
        app_preview_builder.build(self, app_version)
        
        # set the apps preview folder - to the served folder, not the app-kits internal folder
        self.app.preview_version_path = os.path.join(app_preview_builder._preview_app_served_folder(self), 'www')
        self.app.save()

        # optionally increment generic_content versions, if they equal their published version
        for feature_link in self.features():

            generic_content = feature_link.generic_content
            if generic_content.published_version == generic_content.current_version:
                generic_content.current_version = generic_content.current_version + 1
                generic_content.save()

        # reset validation and build result
        self.validation_status = None
        self.build_status = None
        self.build_number = None
        self.save()
        

    def save(self, publish=False, *args, **kwargs):

        if publish == True:
            
            self.published_version = self.current_version
            self.last_published_at = timezone.now()

            # publish all generic contents
            for feature_link in self.features():

                generic_content = feature_link.generic_content
                generic_content.published_version = generic_content.current_version
                generic_content.save()

            # set meta_app.app.published_version_path and meta_app.published_version
            self.app.published_version = self.published_version

            appbuilder = self.get_release_builder()
            published_version_path = appbuilder._published_webapp_www_folder(self)
            self.app.published_version_path = published_version_path

            # set apk_url
            self.app.apk_url = appbuilder.apk_published_url(self, self.published_version)
            # set ipa_url
            self.app.ipa_url = appbuilder.ipa_published_url(self, self.published_version)
            # set pwa_zip_url
            self.app.pwa_zip_url = appbuilder.pwa_zip_published_url(self, self.published_version)
            
            self.app.save()
                
        super().save(*args, **kwargs)
        

    # delete the dumped contents of this app on the commercial installation
    def delete(self):

        # remove all folders of this app
        appbuilder = self.get_preview_builder()
        app_root_folder = appbuilder._app_root_folder(self)

        if os.path.isdir(app_root_folder):
            shutil.rmtree(app_root_folder)

        super().delete()


    # keep only 1 version back
    def remove_old_version_from_disk(self, app_version):
        
        if app_version <= self.current_version -2:
            appbuilder = self.get_preview_builder()
            version_folder = appbuilder._app_version_root_folder(self, app_version)

            if os.path.isdir(version_folder):
                 shutil.rmtree(version_folder)

    @property
    def is_localcosmos_private(self):
        return self.get_global_option('localcosmos_private')


    def __str__(self):
        return self.app.name


    class Meta:
        verbose_name = _('App')
        verbose_name_plural = _('Meta apps')
    



'''--------------------------------------------------------------------------------------------------------------
    APP CONTENT
    - linking app to content
    - taxon_profiles has to be app specific
--------------------------------------------------------------------------------------------------------------'''
class MetaAppGenericContent(models.Model):
    meta_app = models.ForeignKey(MetaApp, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.IntegerField()
    generic_content = GenericForeignKey('content_type', 'object_id')

    options = models.JSONField(null=True)

    def feature_type(self):
        return self.generic_content.feature_type()

    def manage_url(self):
        return 'manage_{0}'.format(self.generic_content.__class__.__name__.lower())


    def __str__(self):
        return '{0}'.format(self.generic_content)

    '''
    def save(self, *args, **kwargs):
        if not self.pk:
            taxon_profiles_ctype = ContentType.objects.get_for_model(TaxonProfiles)
            if self.content_type == taxon_profiles_ctype:

                if MetaAppGenericContent.objects.filter(meta_app=self.meta_app, content_type=taxon_profiles_ctype).exists():
                    raise ValueError('Importing of Taxon Profiles into another app is disallowed')
                
        super().save(*args, **kwargs)
    '''
    
    class Meta:
        unique_together = ('meta_app', 'content_type', 'object_id')




'''--------------------------------------------------------------------------------------------------------------
    GENERIC CONTENT IMAGES AND IMAGESTORE
    - image store is a store for all images
    - a taxon can be assigned (optionally)
    - if a taxon is assigned, the image will occur e.g. in taxon profiles

    - ContentImage links ImageStore objects to content
    - linking content to images
    - for images of identification keys etc
    - as nature guides etc can be shared across apps, images cannot be linked to a specific app
--------------------------------------------------------------------------------------------------------------'''

def get_image_store_path(instance, filename):
    blankname, ext = os.path.splitext(filename)
    
    new_filename = '{0}{1}'.format(instance.md5, ext)
    path = '/'.join(['{0}'.format(connection.schema_name), 'imagestore', '{0}'.format(instance.uploaded_by.pk),
                     new_filename])
    return path


from localcosmos_server.taxonomy.generic import ModelWithTaxon
class ImageStore(ModelWithTaxon):

    LazyTaxonClass = LazyTaxon

    # null Foreignkey means the user does not exist anymore
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    source_image = models.ImageField(upload_to=get_image_store_path)
    md5 = models.CharField(max_length=255)

    licences = GenericRelation(ContentLicenceRegistry) # enables on delete cascade


'''
    Multiple images per content are possible
'''
class ContentImage(models.Model):

    image_store = models.ForeignKey(ImageStore, on_delete=models.CASCADE)
    
    crop_parameters = models.TextField(null=True)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.IntegerField()
    content = GenericForeignKey('content_type', 'object_id')

    # a content can have different images
    # eg an image of type 'background' and an image of type 'logo'
    image_type = models.CharField(max_length=100, default='image')
    
    position = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)


    text = models.CharField(max_length=355, null=True)


    def get_thumb_filename(self, size=400):

        if self.image_store.source_image:
            filename = os.path.basename(self.image_store.source_image.path)
            blankname, ext = os.path.splitext(filename)

            suffix = 'uncropped'
            if self.crop_parameters:
                suffix = hashlib.md5(self.crop_parameters.encode('utf-8')).hexdigest()

            thumbname = '{0}-{1}-{2}{3}'.format(blankname, suffix, size, ext)
            return thumbname
        
        else:
            return 'noimage.png'


    def image_url(self, size=400, force=False):

        image_path = self.image_store.source_image.path
        folder_path = os.path.dirname(image_path)

        thumbname = self.get_thumb_filename(size)

        thumbfolder = os.path.join(folder_path, 'thumbnails')
        if not os.path.isdir(thumbfolder):
            os.makedirs(thumbfolder)

        thumbpath = os.path.join(thumbfolder, thumbname)

        if not os.path.isfile(thumbpath) or force == True:

            imageFile = Image.open(image_path)

            if self.crop_parameters:
                #{"x":253,"y":24,"width":454,"height":454,"rotate":0,"scaleX":1,"scaleY":1}
                crop_parameters = json.loads(self.crop_parameters)
                
                # first crop, then resize
                # box: (left, top, right, bottom)
                box = (
                    crop_parameters['x'],
                    crop_parameters['y'],
                    crop_parameters['x'] + crop_parameters['width'],
                    crop_parameters['y'] + crop_parameters['height'],
                )
                
                cropped = imageFile.crop(box)

            else:
                cropped = imageFile
                
            cropped.thumbnail([size,size], Image.ANTIALIAS)
            
            cropped.save(thumbpath, imageFile.format)
            
        
        thumburl = os.path.join(os.path.dirname(self.image_store.source_image.url), 'thumbnails', thumbname)
        return thumburl
    

'''--------------------------------------------------------------------------------------------------------------
    META CACHE
    - overarching caches, for example for vernacular names
--------------------------------------------------------------------------------------------------------------'''
class MetaCache(models.Model):

    name = models.CharField(max_length=255, unique=True) 
    cache = models.JSONField(null=True)
    updated_at = models.DateTimeField(auto_now=True)

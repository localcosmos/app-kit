from localcosmos_server.taxonomy.generic import ModelWithTaxon
from .settings import ADDABLE_FEATURES, REQUIRED_FEATURES

import matplotlib
matplotlib.use('Agg')
#import matplotlib.style as mplstyle
#mplstyle.use('fast')
import matplotlib.pyplot as plt

from django.conf import settings
from django.db import connection, models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse

from django.contrib.contenttypes.fields import GenericRelation

import os, io, json, numpy, cv2

from django.template.defaultfilters import slugify  # package_name

from .generic import GenericContentMethodsMixin

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy
from taxonomy.models import TaxonomyModelRouter, MetaVernacularNames
from taxonomy.lazy import LazyTaxon, LazyTaxonList

from .utils import import_module

from django_tenants.utils import get_tenant_model, get_tenant_domain_model

from app_kit.app_kit_api.models import AppKitJobs

from localcosmos_server.models import App, SecondaryAppLanguages, SeoParametersAbstract

from PIL import Image, ImageFile, ImageColor
ImageFile.LOAD_TRUNCATED_IMAGES = settings.APP_KIT_LOAD_TRUNCATED_IMAGES

# draw features on image


LOCALIZED_CONTENT_IMAGE_TRANSLATION_PREFIX = 'localized_content_image'

'''--------------------------------------------------------------------------------------------------------------
    MIXINS
--------------------------------------------------------------------------------------------------------------'''

from localcosmos_server.models import ServerContentImageMixin

class ContentImageMixin (ServerContentImageMixin):

    def get_model(self):
        return ContentImage
    


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
            content_images = ContentImage.objects.filter(
                content_type=content_type, object_id=self.pk)

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
    ('failing', _('failing')),  # build failed, see log files
    # build passed, packages have been built and are present
    ('passing', _('passing')),
    ('in_progress', _('build in progress')),  # build is in progress, async
)

APP_VALIDATION_STATUS = (
    ('in_progress', _('validation in progress')),
    ('valid', _('valid')),
    ('warnings', _('warnings')),
    ('errors', _('errors')),
)


'''
    used to create new apps
    - one subdomain per app on LC
'''
def strip_leading_numerals(name):
    """
    Removes leading numerals from the name.
    E.g., '1001seaforest' -> 'seaforest'
    """
    import re
    return re.sub(r'^\d+', '', name)

class MetaAppManager(models.Manager):

    def _create_required_features(self, meta_app, frontend=None):

        # create all required features and link them to the app
        for required_feature in REQUIRED_FEATURES:

            feature_module = import_module(required_feature)
            FeatureModel = feature_module.models.FeatureModel

            kwargs = {}

            feature_name = str(FeatureModel._meta.verbose_name)

            if FeatureModel.__name__ == 'Frontend' and frontend != None:
                kwargs['frontend_name'] = frontend

            feature = FeatureModel.objects.create(
                feature_name, meta_app.primary_language, **kwargs)

            link = MetaAppGenericContent(
                meta_app=meta_app,
                content_type=ContentType.objects.get_for_model(feature),
                object_id=feature.id,
            )
            link.save()

    def create(self, name, primary_language, domain_name, tenant, subdomain, **kwargs):

        secondary_languages = kwargs.pop('secondary_languages', [])
        global_options = kwargs.pop('global_options', {})

        frontend = kwargs.pop('frontend', None)
        
        # Flip leading numerals before slugify
        flipped_name = strip_leading_numerals(name)
        cleaned_name = slugify(flipped_name).replace('-', '').lower()[:30]

        package_name_base = 'org.localcosmos.{0}'.format(cleaned_name)
        package_name = package_name_base

        # make sure it is unique
        exists = self.filter(package_name=package_name).exists()
        i = 2
        while exists:
            package_name = '{0}{1}'.format(package_name_base, i)
            i += 1
            exists = self.filter(package_name=package_name).exists()

        # this also creates the online content link
        extra_app_kwargs = {}
        if 'uuid' in kwargs:
            extra_app_kwargs['uuid'] = kwargs['uuid']
        app = App.objects.create(
            name, primary_language, subdomain, **extra_app_kwargs)

        Domain = get_tenant_domain_model()

        # 2 cases: domain exists as an empty app kit (app_id = None) or does not exist at all

        domain = Domain.objects.filter(
            tenant=tenant, domain=domain_name, app__isnull=True).first()

        if not domain:

            is_primary_domain = Domain.objects.filter(
                tenant=tenant, is_primary=True).exists() == False

            domain = Domain(
                tenant=tenant,
                domain=domain_name,
                is_primary=is_primary_domain,
            )

        domain.app = app
        domain.save()

        # create app and profile
        meta_app = self.model(
            app=app,
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

        self._create_required_features(meta_app, frontend=frontend)

        return meta_app


'''
    META APP
    - uuid, primary_language and name lie in MetaApp.app
    - published versions cannot be changed
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

    # app identifier: localcosmos.package_name
    package_name = models.CharField(max_length=100, unique=True)

    build_settings = models.JSONField(null=True)

    # version_specific build number
    build_number = models.IntegerField(null=True)

    # all localizations of all features, not including images
    localizations = models.JSONField(null=True)

    # links to several stores, using json for future safety
    store_links = models.JSONField(null=True)

    build_status = models.CharField(
        max_length=50, choices=APP_BUILD_STATUS, null=True)
    last_build_report = models.JSONField(null=True)

    validation_status = models.CharField(
        max_length=50, choices=APP_VALIDATION_STATUS, null=True)
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

        build_jobs = AppKitJobs.objects.filter(
            meta_app_uuid=self.uuid, job_type='build')

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
            'meta_app_id': self.pk,
            'content_type_id': content_type.id,
            'object_id': self.pk,
        }

        view_url = reverse('manage_metaapp', kwargs=url_kwargs,
                           urlconf=settings.ROOT_URLCONF)

        url = '{0}{1}'.format(self.domain, view_url)

        return url

    def languages(self):
        return self.app.languages()

    def secondary_languages(self):
        return self.app.secondary_languages()

    def addable_features(self):

        feature_models = []

        for feature in ADDABLE_FEATURES:

            feature_module = import_module(feature)
            FeatureModel = feature_module.models.FeatureModel

            feature_models.append(FeatureModel)

        return feature_models

    # BUILDING

    def lock_generic_contents(self):
        contents = MetaAppGenericContent.objects.filter(meta_app=self)
        for link in contents:
            link.generic_content.is_locked = True
            link.generic_content.save(increment_version=False)

    def unlock_generic_contents(self):
        contents = MetaAppGenericContent.objects.filter(meta_app=self)
        for link in contents:
            link.generic_content.is_locked = False
            link.generic_content.save(increment_version=False)
            
    def publish_generic_contents(self):

        contents = MetaAppGenericContent.objects.filter(meta_app=self)

        for link in contents:
            link.generic_content.save(set_published_version=True)
            

    def get_primary_localization(self, meta_app=None):
        locale = {}

        locale[self.name] = self.name

        return locale

    def get_localized_content_images(self):

        primary_locale = self.localizations[self.primary_language]

        images = {}
        for key, value in primary_locale.items():

            if key.startswith(LOCALIZED_CONTENT_IMAGE_TRANSLATION_PREFIX):

                images[key] = value

        return images

    # all uploads for an app (except "design and text") go to this folder

    def media_path(self):
        path = '/'.join(['apps', str(self.uuid)])
        return path

    def features(self):
        return MetaAppGenericContent.objects.filter(meta_app=self)

    def get_generic_content_link(self, generic_content):
        link = MetaAppGenericContent.objects.filter(
            meta_app=self,
            content_type=ContentType.objects.get_for_model(generic_content),
            object_id=generic_content.id
        ).first()

        return link

    # GENERIC CONTENTS
    def get_generic_content_links(self, model):
        content_type = ContentType.objects.get_for_model(model)
        links = MetaAppGenericContent.objects.filter(meta_app=self, content_type=content_type)
        return links

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
        count = taxonlist.count()

        return count

    # return a LazyTaxonList instance

    def higher_taxa(self, include_draft_contents=True):
        # get a list of all taxa, extract with_descendants
        taxonlist = LazyTaxonList()

        feature_links = MetaAppGenericContent.objects.filter(meta_app=self)

        for link in feature_links:
            generic_content = link.generic_content

            if include_draft_contents == False and link.publication_status == 'draft':
                continue

            lazy_list = generic_content.higher_taxa()

            for queryset in lazy_list.querysets:
                taxonlist.add(queryset)

        return taxonlist

    # returns a LazyTaxonList
    # all generic_contents do need a taxa() method, nothing else

    def taxa(self, include_draft_contents=False):

        taxonlist = LazyTaxonList()

        feature_links = MetaAppGenericContent.objects.filter(meta_app=self)

        for link in feature_links:
            generic_content = link.generic_content

            if include_draft_contents == False and link.publication_status == 'draft':
                continue

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
            models = TaxonomyModelRouter(source)
            taxa = models.TaxonTreeModel.objects.all().order_by('taxon_latname')
        else:
            taxa = self.taxa()

        return taxa

    # search the backbone and all associated contents

    def search_taxon(self, searchtext, language='en', limit=10):

        if searchtext == None:
            return []

        searchtext = searchtext.replace('+', ' ').strip().upper()

        if len(searchtext) < 3:
            return []

        results = []

        # FULL TREE SEARCH

        full_tree = self.backbone().get_global_option('include_full_tree')

        if full_tree:
            source = full_tree
            models = TaxonomyModelRouter(source)

            query = models.TaxonTreeModel.objects.filter(
                taxon_latname__istartswith=searchtext)[:limit]

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
                result = lazy_taxon.as_typeahead_choice(label=label)

                if result not in results:
                    results.append(result)

            if len(results) >= limit:
                return results

        # FIRST: LATNAMES, direct
        # content.taxa() returns LazyTaxonList
        taxonlist = self.taxa()

        taxonlist.filter(**{'taxon_latname__istartswith': searchtext})

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

                label = '{0}'.format(taxon.name)
                lazy_taxon = LazyTaxon(instance=taxon.taxon)
                result = lazy_taxon.as_typeahead_choice(label=label)

                if result not in results:

                    results.append(result)

        return results
    
    def get_meta_vernacular_names(self, languages=[]):
        
        app_taxon_name_uuids = []
        
        for taxon in self.taxa():
            app_taxon_name_uuids.append(str(taxon.name_uuid))
        
        all_vernacular_names = MetaVernacularNames.objects.all()
        
        if languages:
            all_vernacular_names = all_vernacular_names.filter(language__in=languages)
        
        
        all_vernacular_names = all_vernacular_names.order_by('name')
        
        app_vernacular_names = []
        
        for vernacular_name in all_vernacular_names:
            if str(vernacular_name.name_uuid) in app_taxon_name_uuids:
                app_vernacular_names.append(vernacular_name)
                
        return app_vernacular_names

    def save(self, publish=False, *args, **kwargs):

        # do not use increment_version for MetaApp
        # this kwarg is inheriteg form GenericContent and uses for all
        # GenericContents except MetaApp
        increment_version = kwargs.pop('increment_version', False)

        if publish == True:

            self.published_version = self.current_version
            self.last_published_at = timezone.now()

            # publish all generic contents
            # generi content version bumps are now handled in 
            #for feature_link in self.features():

            #    generic_content = feature_link.generic_content
            #    generic_content.published_version = generic_content.current_version
            #    generic_content.save()

            # set meta_app.app.published_version_path and meta_app.published_version
            self.app.published_version = self.published_version

            appbuilder = self.get_release_builder()
            published_version_path = appbuilder._published_browser_served_www_path
            self.app.published_version_path = published_version_path

            # set aab_url
            self.app.aab_url = appbuilder.aab_published_url()
            # set ipa_url
            self.app.ipa_url = appbuilder.ipa_published_url()
            # set pwa_zip_url
            self.app.pwa_zip_url = appbuilder.browser_zip_published_url()

            self.app.save()

        super().save(*args, **kwargs)

    # importing globally results in a circular import

    def get_app_builder(self):
        from .appbuilder import AppBuilder
        app_builder = AppBuilder(self)
        return app_builder

    def get_preview_builder(self):
        from .appbuilder import AppPreviewBuilder
        app_preview_builder = AppPreviewBuilder(self)
        return app_preview_builder

    def get_release_builder(self):
        from .appbuilder import AppReleaseBuilder
        app_release_builder = AppReleaseBuilder(self)
        return app_release_builder

    # delete the dumped contents of this app
    def delete(self):

        # remove all folders of this app
        app_builder = self.get_app_builder()
        app_builder.delete_app()

        super().delete()

    # keep only 1 version back

    def remove_old_versions_from_disk(self):

        app_builder = self.get_app_builder()
        app_version = 1

        while app_version <= self.current_version - 2:
            app_builder.delete_app_version(app_version)
            app_version = app_version + 1

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

    position = models.IntegerField(default=0)

    options = models.JSONField(null=True)

    def feature_type(self):
        return self.generic_content.feature_type()

    def manage_url(self):
        return 'manage_{0}'.format(self.generic_content.__class__.__name__.lower())

    def __str__(self):
        return '{0}'.format(self.generic_content)

    @property
    def publication_status(self):
        if self.options:
            return self.options.get('publication_status', 'publish')
        return 'publish'

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
        ordering=['position']


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


from localcosmos_server.models import ImageStoreAbstract
class ImageStore(ImageStoreAbstract):

    LazyTaxonClass = LazyTaxon
    source_image = models.ImageField(upload_to=get_image_store_path)


'''
    Multiple images per content are possible
'''
# Contentimagecommon is for both ContentImage, LocalizedContentImage

from localcosmos_server.models import ContentImageProcessing
class ContentImageCommon(ContentImageProcessing):

    
    def get_arrow_stroke_width(self):

        # {"x":3,"y":3,"width":1130,"height":1130,"rotate":0,"scaleX":1,"scaleY":1}
        crop_params = json.loads(self.crop_parameters)

        return crop_params['width'] * RELATIVE_ARROW_STROKE_WIDTH

    def get_creator_name_initials(self):

        name_initials = None

        licences = self.image_store.licences

        licence = self.image_store.licences.first()

        if licence:
            name = licence.creator_name
            name_initials = ''.join([name[0].upper()
                                    for name in name.split(' ')])

        return name_initials


    # plotting features using opencv
    # opencv is much faster than matplotlib
    def plot_features(self, pil_image):
        
        numpy_array = numpy.array(pil_image)

        opencv_image = cv2.cvtColor(numpy_array, cv2.COLOR_RGB2BGR)

        if self.features:
            for feature in self.features:

                if feature['type'] == 'arrow':

                    arrow = feature

                    initial_point = (arrow['initialPoint']['x'], arrow['initialPoint']['y'])
                    terminal_point = (arrow['terminalPoint']['x'], arrow['terminalPoint']['y'])

                    linewidth = self.get_arrow_stroke_width()

                    # color in bgr
                    # color is #123456
                    hex_color = arrow['color']
                    rgb_color = ImageColor.getcolor(hex_color, "RGB")
                    bgr_color = (rgb_color[2], rgb_color[1], rgb_color[0])

                    cv2.arrowedLine(opencv_image, initial_point, terminal_point, bgr_color, round(linewidth))

        # encode
        is_success, buffer = cv2.imencode(".png", opencv_image)
        io_buf = io.BytesIO(buffer)

        return io_buf

    # add features to a square pil canvas, return a buffer
    def plot_features_matplotlib(self, pil_image):

        width, height = pil_image.size

        in_memory_file = io.BytesIO()
        pil_image.save(in_memory_file, format='PNG')
        in_memory_file.seek(0)

        # first, add all features
        # the coordinates/definitions of a feature are relative to the original image

        dpi = plt.rcParams['figure.dpi']

        img = matplotlib.image.imread(in_memory_file)

        img_height, img_width, bands = img.shape

        fig = plt.figure(dpi=dpi, figsize=[img_width/dpi, img_height/dpi])

        # remove whitespace between axes and figure edge
        fig.add_axes([0,0,1,1])

        # remove axis
        plt.axis('off')

        # remove whitespace around plot
        plt.tight_layout()

        # plot the image
        imgplot = plt.imshow(img)

        # plot the arrows
        '''
        [{"type": "arrow", "color": "#c061cb", "initialPoint": {"x": -23, "y": 74}, "terminalPoint": {"x": 399, "y": 449}}, {"type": "arrow", "color": "#ffa348", "initialPoint": {"x": 1074, "y": 336}, "terminalPoint": {"x": 727, "y": 782}}]
        '''

        if self.features:
            for feature in self.features:
                if feature['type'] == 'arrow':

                    arrow = feature

                    initialPoint = arrow['initialPoint']
                    terminalPoint = arrow['terminalPoint']

                    vector = {
                        'x': terminalPoint['x'] - initialPoint['x'],
                        'y': terminalPoint['y'] - initialPoint['y']
                    }

                    # do not allow off-canvas initialPoints
                    if initialPoint['x'] < 0 or initialPoint['y'] < 0:

                        if initialPoint['x'] < initialPoint['y']:
                            lambda_factor = - (initialPoint['x'] / vector['x'])

                        else:
                            lambda_factor = - (initialPoint['y'] / vector['y'])

                        initialPoint['x'] = initialPoint['x'] + \
                            (vector['x'] * lambda_factor)
                        initialPoint['y'] = initialPoint['y'] + \
                            (vector['y'] * lambda_factor)

                    elif initialPoint['x'] > width or initialPoint['y'] > height:

                        if initialPoint['x'] > initialPoint['y']:
                            lambda_factor = (
                                (initialPoint['x'] - width) / vector['x'])

                        else:
                            lambda_factor = (
                                (initialPoint['y'] - height) / vector['y'])

                        initialPoint['x'] = initialPoint['x'] - \
                            (vector['x'] * lambda_factor)
                        initialPoint['y'] = initialPoint['y'] - \
                            (vector['y'] * lambda_factor)

                    dx = terminalPoint['x'] - initialPoint['x']
                    dy = terminalPoint['y'] - initialPoint['y']

                    linewidth = self.get_arrow_stroke_width()
                    head_width = linewidth * 3

                    plt.arrow(arrow['initialPoint']['x'], arrow['initialPoint']['y'], dx, dy, linewidth=linewidth,
                              head_width=head_width, head_length=head_width, fill=True, length_includes_head=True, color=arrow['color'])

        # plot name initials
        # plot creator on image
        '''
        name_initials = self.get_creator_name_initials()
        if name_initials:

            offset_x = int(width/40)
            offset_y = int(height/40)

            if self.crop_parameters:
                crop_parameters = json.loads(self.crop_parameters)
                offset_x = int(crop_parameters['width'] + crop_parameters['x'] - offset_x)
                offset_y = int(crop_parameters['y'] + offset_y)

            fontsize = int(width * REALTIVE_FONT_SIZE)
            print('plotting {0}, x: {1}, y: {2}'.format(
                name_initials, offset_x, offset_y))

            bbox = {
                'facecolor': 'black',
                'alpha': 0.2,
                'pad': .1,
                'boxstyle': 'round'
            }

            plt.text(offset_x, offset_y, name_initials, fontsize=fontsize, ha='right', va='top', color='#efefef',
                     bbox=bbox)
        '''

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        plt.close('all')

        return buf


    def get_image_locale_key(self):
        locale_key = '{0}_{1}_{2}_{3}'.format(LOCALIZED_CONTENT_IMAGE_TRANSLATION_PREFIX, self.content_type.id,
                                              self.object_id, self.image_type)

        return locale_key

    def get_image_locale_entry(self):

        locale_entry = {
            'image_type': self.image_type,
            'content_type_id': self.content_type.id,
            'object_id': self.object_id,
            'content_image_id': self.id,
            'media_url': self.image_url(),
        }

        return locale_entry


RELATIVE_ARROW_STROKE_WIDTH = 0.02
RELATIVE_ARROW_LENGTH = 0.5
REALTIVE_FONT_SIZE = 0.05

from localcosmos_server.models import ContentImageAbstract
class ContentImage(ContentImageCommon, ContentImageAbstract):
    
    image_store = models.ForeignKey(ImageStore, on_delete=models.CASCADE)
    


'''
    translations of content images
    - require an on image_store link
    - referred content is the same (-> ContentImage Foreign Key)
'''


class LocalizedContentImage(ContentImageCommon, models.Model):

    content_image = models.ForeignKey(ContentImage, on_delete=models.CASCADE)
    language_code = models.CharField(max_length=15)

    # the source image of the translation
    image_store = models.ForeignKey(ImageStore, on_delete=models.CASCADE)

    crop_parameters = models.TextField(null=True)

    # for things like arrows/vectors on the image
    # arrows are stored as [{"type" : "arrow" , "initialPoint": {x:1, y:1}, "terminalPoint": {x:2,y:2}, color: string}]
    features = models.JSONField(null=True)

    class Meta:
        unique_together = ('content_image', 'language_code')



class AppKitSeoParameters(SeoParametersAbstract):
    pass

'''--------------------------------------------------------------------------------------------------------------
    META CACHE
    - overarching caches, for example for vernacular names
--------------------------------------------------------------------------------------------------------------'''


class MetaCache(models.Model):

    name = models.CharField(max_length=255, unique=True)
    cache = models.JSONField(null=True)
    updated_at = models.DateTimeField(auto_now=True)


class SingleFeatureMixin:

    @property
    def meta_app(self):

        content_type = ContentType.objects.get_for_model(self)

        generic_content_link = MetaAppGenericContent.objects.get(
            content_type=content_type, object_id=self.id)
        meta_app = generic_content_link.meta_app

        return meta_app

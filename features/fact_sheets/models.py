from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.template import Context

from django.template import Template, TemplateDoesNotExist
from django.template.backends.django import DjangoTemplates

from app_kit.generic import GenericContentManager, GenericContent, LocalizeableImage

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from content_licencing.models import ContentLicenceRegistry

from taxonomy.lazy import LazyTaxonList

from django.template.defaultfilters import slugify

from .parser import FactSheetTemplateParser

import os


class FactSheets(GenericContent):        

    '''
    Fact Sheets uses different kinds of layoutability wich have to be represented in the translation
    interface. thetefore, the values of the keys have to be {}, which holds the necesssary information
    _meta{} stores layoutability options and image information
    keys in _meta aree the same as in the localization
    '''
    def get_primary_localization(self, meta_app):

        locale = {
            '_meta' : {}, # layoutability options are stored in meta
        }

        locale[self.name] = self.name

        all_fact_sheets = FactSheet.objects.filter(fact_sheets=self)

        fact_sheet_images_content_type = ContentType.objects.get_for_model(FactSheetImages)

        # due to layoutability, the underlying template has to be read
        for fact_sheet in all_fact_sheets:

            # get cms tags out of template and create a layoutability map
            parser = FactSheetTemplateParser(meta_app, fact_sheet)
            cms_tags = parser.parse()

            layoutability_map = {}

            for tag in cms_tags:
                # only text/html content supports layoutability
                if tag.microcontent_category in ['microcontent', 'microcontents']:

                    if 'layoutable-simple' in tag.args:
                        layoutability_map[tag.microcontent_type] = 'layoutable-simple'
                    elif 'layoutable-full' in tag.args:
                        layoutability_map[tag.microcontent_type] = 'layoutable-full'
                    else:
                        layoutability_map[tag.microcontent_type] = None
                    
            
            locale[fact_sheet.title] = fact_sheet.title
            locale[fact_sheet.navigation_link_name] = fact_sheet.navigation_link_name

            # contents
            for microcontent_type, html_content in fact_sheet.contents.items():
                locale_key = fact_sheet.get_locale_key(microcontent_type)

                locale[locale_key] = html_content

                if microcontent_type in layoutability_map:
                    locale['_meta'][locale_key] = {
                        'layoutability' : layoutability_map[microcontent_type],
                        'type' : 'html',
                    }                    

            # fact sheet images which require translation
            fact_sheet_images = FactSheetImages.objects.filter(fact_sheet=fact_sheet,
                                                               requires_translation=True)

            fact_sheet_images_content_type = ContentType.objects.get_for_model(FactSheetImages)

            for fact_sheet_image in fact_sheet_images:

                # add image to locale if it needs translation
                if fact_sheet_image.requires_translation == True:

                    fact_sheet_image.build = True
                    fact_sheet_image.language_code = self.primary_language

                    localizeable_image = LocalizeableImage(fact_sheet_image)
                    
                    locale_key = localizeable_image.get_language_independant_filename()

                    # this has to be a url relative to the apps www folder, and the image has to exist there
                    locale[locale_key] = fact_sheet_image.url

                    locale['_meta'][locale_key] = {
                        'type' : 'image',
                        'media_url' : fact_sheet_image.image.url,
                        'content_type_id' : fact_sheet_images_content_type.id,
                        'object_id' : fact_sheet_image.id,
                    }                    

        return locale


    def taxa(self):
        return LazyTaxonList()


    def higher_taxa(self):
        return LazyTaxonList()


    def get_template(self, meta_app, template_name):

        templates_base_dir = meta_app.get_fact_sheet_templates_path()
        user_uploaded_templates_base_dir = get_user_uploaded_templates_base_dir(self)

        # first, check custom templates
        db_template = FactSheetTemplates.objects.filter(fact_sheets=self, template=template_name).first()

        if db_template:
            template_path = db_template.template.path

        else:
            template_path = os.path.join(templates_base_dir, template_name)

        if not os.path.isfile(template_path):
            msg = 'Fact Sheet Template {0} does not exist. Tried: {1}'.format(template_name, template_path)
            
            raise TemplateDoesNotExist(msg)


        params = {
            'NAME' : 'FactSheetsEngine',
            #'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [templates_base_dir, user_uploaded_templates_base_dir],
            'APP_DIRS': False,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
                'loaders' : [
                    'django.template.loaders.filesystem.Loader',
                ]
            },
        }
        engine = DjangoTemplates(params)

        with open(template_path, encoding=engine.engine.file_charset) as fp:
            contents = fp.read()

        # use the above engine with dirs
        template = Template(contents, engine=engine.engine)
        
        return template


    class Meta:
        verbose_name = _('Fact sheets')
        verbose_name_plural = _('Fact sheets')


FeatureModel = FactSheets


'''
    Template based offline content
    - during build, .html files are produced
    - how to deal with in-content-images?
      - store them as FactSheetImages with content = content_id
      - in the html, the data-image-id attribute is used as a reference to the image
'''
class FactSheet(models.Model):

    fact_sheets = models.ForeignKey(FactSheets, on_delete=models.CASCADE)
    
    template_name = models.CharField(max_length=355)

    title = models.CharField(max_length=355)
    navigation_link_name = models.CharField(max_length=355, null=True)

    slug = models.SlugField(unique=True, null=True) # null, because pk appears in slug

    # holds the html parts of the template content
    '''
    {
        'content_id' : 'html',
        'content_id' : ['html', 'html'],
    }
    '''
    contents = models.JSONField(null=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    def get_locale_key(self, microcontent_type):

        locale_key = '{0}_{1}'.format(self.id, microcontent_type)
        return locale_key


    def get_template(self, meta_app):

        return self.fact_sheets.get_template(meta_app, self.template_name)
        

    def get_atomic_content(self, microcontent_type):
        
        if microcontent_type in self.contents:
            return self.contents[microcontent_type]
        
        return None

    def render_as_html(self, meta_app):
        template = self.get_template(meta_app)

        context = {
            'fact_sheet' : self,
        }

        c = Context(context)
        rendered = template.render(c)

        return rendered


    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        if not self.slug:
            self.slug = '{0}-{1}'.format(slugify(self.title), self.pk)
            super().save(*args, **kwargs)


    def __str__(self):
        return self.title


    class Meta:
        verbose_name = _('Fact sheet')
        verbose_name_plural = _('Fact sheets')



def factsheet_images_upload_path(instance, filename):

    generic_content_id = instance.fact_sheet.fact_sheets.id
    fact_sheet_id = instance.fact_sheet.id

    base_path = os.path.join('fact_sheets', 'content', str(generic_content_id), str(fact_sheet_id), 'images')
    path = os.path.join(base_path, instance.microcontent_type, filename)

    return path

'''
    primary language
    - maybe mark an image as translatable
'''
class FactSheetImages(models.Model):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # flag if the image is called during the build process of the app
        self.build = False
        # no language
        self.language_code = self.fact_sheet.fact_sheets.primary_language

    fact_sheet = models.ForeignKey(FactSheet, on_delete=models.CASCADE)
    
    # bind image to microcontent_type of template (user adds image in text box) or microcontent_type
    microcontent_type = models.CharField(max_length=355)
    
    image = models.ImageField(upload_to=factsheet_images_upload_path)
    text = models.CharField(max_length=355, null=True)
    
    # mark an image as translatable
    requires_translation = models.BooleanField(default=False)
    
    licences = GenericRelation(ContentLicenceRegistry)

    # during build, url has to be different from preview
    # the html rendering during build fetches the url using this method
    # the translated images require the path accordingly
    @property
    def url(self):

        if self.build == False:
            return self.image.url

        # during build, the url has to be according to the app file/folder layout
        # also called By AppReleaseBuilder and FactSheetsJSONBuilder
        filename = os.path.basename(self.image.name)

        if self.requires_translation == True:

            localizeable_image = LocalizeableImage(self)
            url = localizeable_image.get_relative_localized_image_path(self.language_code)
            
        else:
            # no language_code required
            url = 'features/FactSheets/{0}/{1}-{2}/images/{3}'.format(
                str(self.fact_sheet.fact_sheets.uuid), str(self.fact_sheet.pk), slugify(self.fact_sheet.title),
                filename)

        return url


def get_user_uploaded_templates_base_dir(fact_sheets):
    return os.path.join('fact_sheets', 'templates', str(fact_sheets.id))


def build_factsheets_templates_upload_path(fact_sheets, filename):

    base_dir = get_user_uploaded_templates_base_dir(fact_sheets)
    path = os.path.join(base_dir, filename)

    return path


def factsheet_templates_upload_path(instance, filename):
    return build_factsheets_templates_upload_path(instance.fact_sheets, filename)


class FactSheetTemplates(models.Model):

    fact_sheets = models.ForeignKey(FactSheets, on_delete=models.CASCADE)
    template = models.FileField(upload_to=factsheet_templates_upload_path)
    name = models.CharField(max_length=255, null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('fact_sheets', 'template')

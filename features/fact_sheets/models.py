from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.template import Context

from django.template import Template, TemplateDoesNotExist
from django.template.backends.django import DjangoTemplates

from app_kit.generic import GenericContent, AppContentTaxonomicRestriction

from app_kit.models import ContentImageMixin


from django.contrib.contenttypes.models import ContentType

from taxonomy.lazy import LazyTaxonList

from django.template.defaultfilters import slugify

from .parser import FactSheetTemplateParser

import os


class FactSheets(GenericContent):        

    '''
    Fact Sheets uses different kinds of layoutability wich have to be represented in the translation
    interface. thetefore, the values of the keys have to be {}, which holds the necesssary information
    _meta{} stores layoutability options and image information
    keys in _meta are the same as in the localization
    '''
    def get_primary_localization(self, meta_app):

        locale = {
            '_meta' : {}, # layoutability options are stored in meta
        }

        locale[self.name] = self.name

        all_fact_sheets = FactSheet.objects.filter(fact_sheets=self)

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
            if fact_sheet.contents:
                for microcontent_type, html_content in fact_sheet.contents.items():
                    locale_key = fact_sheet.get_locale_key(microcontent_type)

                    locale[locale_key] = html_content

                    if microcontent_type in layoutability_map:
                        locale['_meta'][locale_key] = {
                            'layoutability' : layoutability_map[microcontent_type],
                            'type' : 'html',
                        }                    

            # fact sheet images which require translation
            fact_sheet_images = fact_sheet.all_images()

            translation_images = fact_sheet_images.filter(requires_translation=True)

            for fact_sheet_image in translation_images:
                
                locale_key = fact_sheet_image.get_image_locale_key()

                locale_entry = fact_sheet_image.get_image_locale_entry()

                # there is no built image yet, use media_url for the translation matrix
                locale[locale_key] = locale_entry                    

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



class FactSheetManager(models.Manager):
    
    def filter_by_taxon(self, lazy_taxon, ascendants=False):

        fact_sheets = []

        if ascendants == False:

            fact_sheet_content_type = ContentType.objects.get_for_model(FactSheet)
            
            taxon_latname = lazy_taxon.taxon_latname
            taxon_author=lazy_taxon.taxon_author
            taxon_source = lazy_taxon.taxon_source

            fact_sheet_links = AppContentTaxonomicRestriction.objects.filter(content_type=fact_sheet_content_type,
                taxon_source=taxon_source, taxon_latname=taxon_latname, taxon_author=taxon_author)

            fact_sheet_ids = fact_sheet_links.values_list('object_id', flat=True)

            fact_sheets = self.filter(pk__in=fact_sheet_ids)


        else:
            # get for all nuids, not implemented yet
            taxon_nuid = lazy_taxon.taxon_nuid

        
        return fact_sheets

'''
    Template based offline content
    - during build, .html files are produced
    - how to deal with in-content-images?
      - use ContentImage, bound to fact sheet id, image_type == microcontent_type
      - in the html, the data-image-id attribute is used as a reference to the image
'''
class FactSheet(models.Model, ContentImageMixin):

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

    objects = FactSheetManager()

    def get_locale_key(self, microcontent_type):

        locale_key = '{0}_{1}'.format(self.id, microcontent_type)
        return locale_key


    def get_template(self, meta_app):

        template = self.fact_sheets.get_template(meta_app, self.template_name)

        return template
        

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


    def get_content_image_restrictions(self, image_type):
        
        restrictions = {
            'allow_features' : False,
            'allow_cropping' : False,
        }

        return restrictions


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

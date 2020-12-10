from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.template import Context

from django.template import Template, TemplateDoesNotExist
from django.template.backends.django import DjangoTemplates

from app_kit.generic import GenericContentManager, GenericContent

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon

from django.contrib.contenttypes.fields import GenericRelation
from content_licencing.models import ContentLicenceRegistry

from taxonomy.lazy import LazyTaxonList

from django.template.defaultfilters import slugify

import os

class FactSheets(GenericContent):

    def get_primary_localization(self):

        locale = {}

        locale[self.name] = self.name

        return locale


    def taxa(self):
        return LazyTaxonList()


    def higher_taxa(self):
        return LazyTaxonList()


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


    def get_template(self, meta_app):

        templates_base_dir = meta_app.get_fact_sheet_templates_path()

        template_path = os.path.join(templates_base_dir, self.template_name)

        if not os.path.isfile(template_path):
            msg = 'Fact Sheet Template {0} does not exist. Tried: {1}'.format(self.template_name,
                                                                              template_path)
            raise TemplateDoesNotExist(msg)


        params = {
            'NAME' : 'FactSheetsEngine',
            #'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [templates_base_dir],#, user_uploaded_templates_base_dir],
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


class FactSheetImages(models.Model):

    fact_sheet = models.ForeignKey(FactSheet, on_delete=models.CASCADE)
    
    # bind image to microcontent_type of template (user adds image in text box) or microcontent_type
    microcontent_type = models.CharField(max_length=355)
    
    image = models.ImageField(upload_to=factsheet_images_upload_path)
    text = models.CharField(max_length=355, null=True)
    
    licences = GenericRelation(ContentLicenceRegistry)


def factsheet_templates_upload_path(instance, filename):

    generic_content_id = instance.fact_sheets.id

    path = os.path.join('fact_sheets', 'templates', str(generic_content_id), filename)

    return path


class FactSheetTemplates(models.Model):

    fact_sheets = models.ForeignKey(FactSheets, on_delete=models.CASCADE)
    template = models.FileField(upload_to=factsheet_templates_upload_path)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

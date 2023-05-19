import os

from app_kit.models import ContentImage

from app_kit.generic import AppContentTaxonomicRestriction
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.template_content.models import TemplateContent

from django.utils.text import slugify


class JSONBuilder:

    def __init__(self, app_release_builder, app_generic_content):

        self.app_release_builder = app_release_builder
        self.app_generic_content = app_generic_content
        self.generic_content = app_generic_content.generic_content
        self.meta_app = app_generic_content.meta_app


    '''
    build the json representation of the actual content
    '''
    def build(self):
        raise NotImplementedError('JSONBuilder subclasses do need a build method')

    def build_features_json_entry(self):

        generic_content_type = self.generic_content.__class__.__name__

        description = None

        if self.generic_content.global_options and 'description' in self.generic_content.global_options:

            description = self.generic_content.get_global_option('description')

        features_json_entry = {
            'genericContentType' : generic_content_type,
            'uuid' : str(self.generic_content.uuid),
            'name' : self.generic_content.name,
            'description': description,
            'slug' : self.app_release_builder.get_generic_content_slug(self.generic_content),
            'version' : self.generic_content.current_version,
        }
 
        # add localized names directly in the feature.js
        '''
        for language_code in self.meta_app.languages():
            localized_name = self.get_localized(generic_content.name, language_code)
            
            feature_entry['name'][language_code] = localized_name
        '''

        return features_json_entry



    # language independant
    def _build_common_json(self):

        options = self.get_options()

        global_options = self.get_global_options()
        
        generic_content_json = {
            'uuid' : str(self.generic_content.uuid),
            'version' : self.generic_content.current_version,
            'options' : options,
            'globalOptions' : global_options,
            'name' : self.generic_content.name, #{}, translated in-app
            'slug' : self.app_release_builder.get_generic_content_slug(self.generic_content),
        }

        return generic_content_json

    def _get_content_image(self, content_image_mixedin, image_type='image'):

        if type(content_image_mixedin) == ContentImage:
            content_image = content_image_mixedin
        else:
            content_image = content_image_mixedin.image(image_type=image_type)

        return content_image


    def _get_image_urls(self, content_image_mixedin, image_type='image', image_sizes='regular'):

        content_image = self._get_content_image(content_image_mixedin, image_type=image_type)

        if content_image:
            image_urls = self.app_release_builder.build_content_image(content_image, image_sizes=image_sizes)

        else:
            image_urls = self.app_release_builder.no_image_url
            
        return image_urls 


    def _get_image_licence(self, content_image_mixedin, image_type='image'):
        if type(content_image_mixedin) == ContentImage:
            content_image = content_image_mixedin
        else:
            content_image = content_image_mixedin.image(image_type=image_type)

        licence = self.app_release_builder.content_image_builder.build_licence(content_image)
        return licence


    def get_taxonomic_restriction(self, instance, restriction_model=AppContentTaxonomicRestriction):

        content_type = ContentType.objects.get_for_model(instance)
        taxonomic_restriction_query = restriction_model.objects.filter(
            content_type = content_type,
            object_id = instance.id,
        )

        taxonomic_restriction_json = []

        for restriction in taxonomic_restriction_query:

            taxon_json = {
                'taxonSource' : restriction.taxon_source,
                'taxonLatname' : restriction.taxon_latname,
                'taxonAuthor' : restriction.taxon_author,
                'nameUuid' : str(restriction.name_uuid),
                'taxonNuid' : restriction.taxon_nuid,
                'restrictionType' : restriction.restriction_type,
            }

            taxonomic_restriction_json.append(taxon_json)

        return taxonomic_restriction_json


    def get_template_content_json_for_taxon(self, taxon):

        template_contents = []

        template_contents_query = TemplateContent.objects.filter_by_taxon(taxon)

        for template_content in template_contents_query:
            template_content_json = self.get_template_content_json(template_content)
            template_contents.append(template_content_json)

        return template_contents


    def get_template_content_json(self, template_content):

        ltc = template_content.get_locale(self.meta_app.primary_language)

        template_content_json = {
            'slug' : ltc.slug,
            'title' : ltc.published_title,
        }

        return template_content_json


    def to_camel_case(self, string):
        return self.app_release_builder.to_camelcase(string)


    def get_options(self):
        
        options = {}

        if self.app_generic_content.options:

            for key, value in self.app_generic_content.options.items():

                camel_case_key = self.to_camel_case(key)
                options[camel_case_key] = value

        return options


    def get_global_options(self):
        
        global_options = {}
        
        if self.generic_content.global_options:

            for key, value in self.generic_content.global_options.items():

                camel_case_key = self.to_camel_case(key)

                global_options[camel_case_key] = value
        
        return global_options

    
    def build_taxon(self, lazy_taxon):

        taxon = {
            'taxonSource': lazy_taxon.taxon_source,
            'taxonLatname': lazy_taxon.taxon_latname,
            'taxonAuthor': lazy_taxon.taxon_author,
            'nameUuid' : str(lazy_taxon.name_uuid),
            'taxonNuid' : lazy_taxon.taxon_nuid,
        }

        return taxon
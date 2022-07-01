import os

from app_kit.models import ContentImage

from app_kit.generic import AppContentTaxonomicRestriction
from django.contrib.contenttypes.models import ContentType

from app_kit.features.fact_sheets.models import FactSheet


class JSONBuilder:

    def __init__(self, app_release_builder, app_generic_content):

        self.app_release_builder = app_release_builder
        self.app_generic_content = app_generic_content
        self.generic_content = app_generic_content.generic_content
        self.meta_app = app_generic_content.meta_app


    '''
    build the json representation of the actual content
    the feature entry for features.js is built by the appbuilder class
    '''
    def build(self):
        raise NotImplementedError('JSONBuilder subclasses do need a build method')


    # language independant
    def _build_common_json(self):

        options = {}
        if self.app_generic_content.options:
            options = self.app_generic_content.options

        global_options = {}
        if self.generic_content.global_options:
            global_options = self.generic_content.global_options
        
        generic_content_json = {
            'uuid' : str(self.generic_content.uuid),
            'version' : self.generic_content.current_version,
            'options' : options,
            'global_options' : global_options,
            'name' : self.generic_content.name, #{}, translated in-app
        }

        return generic_content_json

    def _get_content_image(self, content_image_mixedin, image_type='image'):

        if type(content_image_mixedin) == ContentImage:
            content_image = content_image_mixedin
        else:
            content_image = content_image_mixedin.image(image_type=image_type)

        return content_image


    def _get_image_url(self, content_image_mixedin, image_type='image', filename=None, size=None):

        content_image = self._get_content_image(content_image_mixedin, image_type=image_type)

        if content_image:
            image_url = self.app_release_builder.save_content_image(content_image, filename=filename, size=size)
        else:
            image_url = self.app_release_builder.no_image_url
            
        return image_url        


    def get_taxonomic_restriction(self, instance):

        content_type = ContentType.objects.get_for_model(instance)
        taxonomic_restriction_query = AppContentTaxonomicRestriction.objects.filter(
            content_type = content_type,
            object_id = instance.id,
        )

        taxonomic_restriction = []

        for restriction in taxonomic_restriction_query:

            taxon_dic = {
                'taxon_source' : restriction.taxon_source,
                'taxon_latname' : restriction.taxon_latname,
                'taxon_author' : restriction.taxon_author,

                'name_uuid' : restriction.name_uuid,
                'taxon_nuid' : restriction.taxon_nuid,
                
                'restriction_type' : restriction.restriction_type,
            }

            taxonomic_restriction.append(taxon_dic)

        return taxonomic_restriction


    def get_fact_sheets_json_for_taxon(self, taxon):

        fact_sheets = []

        fact_sheets_query = FactSheet.objects.filter_by_taxon(taxon)

        for fact_sheet in fact_sheets_query:
            fact_sheet_json = self.get_fact_sheet_json(fact_sheet)
            fact_sheets.append(fact_sheet_json)

        return fact_sheets


    def get_fact_sheet_json(self, fact_sheet):

        fact_sheet_json = {
            'id' : fact_sheet.id,
            'title' : fact_sheet.title,
        }

        return fact_sheet_json
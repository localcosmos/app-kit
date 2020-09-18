import os

from app_kit.models import ContentImage

from app_kit.generic import AppContentTaxonomicRestriction
from django.contrib.contenttypes.models import ContentType


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

        '''
        # add the name for all languages
        for language_code in self.meta_app.languages():

            localized_name = self.app_release_builder.get_localized(self.meta_app, self.generic_content.name,
                                                                    language_code)
            
            # add the name for the given language_code
            generic_content_json['name'][language_code] = localized_name
        ''' 

        return generic_content_json



    def _get_image_url(self, content_image_mixedin, size=None):

        if type(content_image_mixedin) == ContentImage:
            content_image = content_image_mixedin
        else:
            content_image = content_image_mixedin.image()

        if content_image:
            image_url = self.app_release_builder.save_content_image(content_image, size=size)
        else:
            image_url = 'img/noimage.svg'
            
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
        
        
        

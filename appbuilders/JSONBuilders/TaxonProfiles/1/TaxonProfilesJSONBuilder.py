from django.contrib.contenttypes.models import ContentType

from app_kit.appbuilders.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.taxon_profiles.models import TaxonProfile
from app_kit.features.nature_guides.models import (NatureGuidesTaxonTree, MatrixFilter, NodeFilterSpace,
                                                   NatureGuide)
from app_kit.models import ContentImage, MetaAppGenericContent

'''
    Builds JSON for one TaxonProfiles
'''
class TaxonProfilesJSONBuilder(JSONBuilder):

    small_image_size = (200,200)
    large_image_size = (1000, 1000)


    def build(self):
        return self._build_common_json()


    # languages is for the vernacular name only, the rest are keys for translation
    def build_taxon_profile(self, profile_taxon, gbiflib, languages):

        # get the profile
        db_profile = TaxonProfile.objects.filter(taxon_source=profile_taxon.taxon_source,
                    taxon_latname=profile_taxon.taxon_latname, taxon_author=profile_taxon.taxon_author).first()

        taxon_profile = {
            'taxon_source' : profile_taxon.taxon_source,
            'taxon_latname' : profile_taxon.taxon_latname,
            'taxon_author' : profile_taxon.taxon_author,
            'name_uuid' : profile_taxon.name_uuid,
            'taxon_nuid' : profile_taxon.taxon_nuid,
            'vernacular' : {},
            'node_names' : [], # if the taxon occurs in a nature guide, primary_language only
            'node_decision_rules' : [],
            'traits' : [], # a collection of traits (matrix filters)
            'texts': [],
            'images' : {
                'taxon_profile_images' : [],
                'node_images' : [],
                'taxon_images' : [],
            },
            'gbif_nubKey' : None,
        }

        for language_code in languages:
            vernacular_name = profile_taxon.vernacular(language=language_code)

            taxon_profile['vernacular'][language_code] = vernacular_name

        collected_content_image_ids = set([])
        # get taxon_profile_images
        if db_profile:
            for content_image in db_profile.images():
                image_entry = {
                    'text' : content_image.text,
                    'image_url' : self._get_image_url(content_image),
                    'small_url' : self._get_image_url(content_image, self.small_image_size),
                    'large_url' : self._get_image_url(content_image, self.large_image_size),
                }

                taxon_profile['images']['taxon_profile_images'].append(image_entry)

                collected_content_image_ids.add(content_image.id)

        

        # get information (traits, node_names) from nature guides if possible
        # collect node images
        # only use occurrences in nature guides of this app
        nature_guide_type = ContentType.objects.get_for_model(NatureGuide)
        nature_guide_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app,
                                                                  content_type=nature_guide_type)
        nature_guide_ids = nature_guide_links.values_list('object_id', flat=True)
        
        node_occurrences = NatureGuidesTaxonTree.objects.filter(nature_guide_id__in=nature_guide_ids,
                        taxon_latname=profile_taxon.taxon_latname, taxon_author=profile_taxon.taxon_author)


        for node in node_occurrences:
            if node.meta_node.name not in taxon_profile['node_names']:
                taxon_profile['node_names'].append(node.meta_node.name)

            node_image = node.meta_node.image()

            if node_image is not None and node_image.id not in collected_content_image_ids:
                collected_content_image_ids.add(node_image.id)
                image_entry = {
                    'text' : node_image.text,
                    'image_url' : self._get_image_url(node_image),
                    'small_url' : self._get_image_url(node_image, self.small_image_size),
                    'large_url' : self._get_image_url(node_image, self.large_image_size),
                }

                taxon_profile['images']['node_images'].append(image_entry)

            if node.decision_rule and node.decision_rule not in taxon_profile['node_decision_rules']:
                taxon_profile['node_decision_rules'].append(node.decision_rule)

            matrix_filters = MatrixFilter.objects.filter(meta_node=node.parent.meta_node)

            for matrix_filter in matrix_filters:
                node_spaces = NodeFilterSpace.objects.filter(node=node, matrix_filter=matrix_filter)


                node_trait = {
                    'matrix_filter' : {
                        'name' : matrix_filter.name,
                        'is_multispace' : matrix_filter.matrix_filter_type.is_multispace,
                        'description' : matrix_filter.description,
                        'filter_type' : matrix_filter.filter_type,
                        'definition' : matrix_filter.definition,
                    },
                }

                if matrix_filter.matrix_filter_type.is_multispace == True:
                    node_trait['values'] = []

                for node_space in node_spaces:

                    if matrix_filter.matrix_filter_type.is_multispace == True:
                        
                        for value in node_space.values.all():
                            values_entry = {
                                'encoded_space': value.encoded_space,
                                'image_url' : self._get_image_url(value),
                            }

                            if matrix_filter.filter_type == 'ColorFilter':
                                encoded_space = value.encoded_space
                                values_entry['rgba'] = 'rgba({0},{1},{2},{3})'.format(encoded_space[0],
                                                        encoded_space[1], encoded_space[2], encoded_space[3])
                                
                            node_trait['values'].append(values_entry)

                    else:
                        node_trait['values'] = node_space.encoded_space
                        

                taxon_profile['traits'].append(node_trait)


        # get taxonomic images
        taxon_images = ContentImage.objects.filter(image_store__taxon_source=profile_taxon.taxon_source,
                                    image_store__taxon_latname=profile_taxon.taxon_latname,
                                    image_store__taxon_author=profile_taxon.taxon_author).exclude(
                                    pk__in=list(collected_content_image_ids))

        for taxon_image in taxon_images:
            image_entry = {
                'text': taxon_image.text,
                'image_url' : self._get_image_url(taxon_image),
                'small_url' : self._get_image_url(taxon_image, self.small_image_size),
                'large_url' : self._get_image_url(taxon_image, self.large_image_size),
            }

        # get the gbif nubKey
        if self.app_release_builder.use_gbif == True:
            gbif_nubKey = gbiflib.get_nubKey(profile_taxon)
            if gbif_nubKey :
                taxon_profile['gbif_nubKey'] = gbif_nubKey


        if db_profile:

            for text in db_profile.texts():

                if text.text:

                    text_dic = {
                        'taxon_text_type' : text.taxon_text_type.text_type,
                        'text' : text.text,
                        'text_key' : self.generic_content.get_text_key(text),
                    }

                    taxon_profile['texts'].append(text_dic)


        return taxon_profile

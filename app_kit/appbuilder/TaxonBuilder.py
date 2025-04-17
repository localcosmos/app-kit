from django.conf import settings
from app_kit.appbuilder.GBIFlib import GBIFlib
from app_kit.features.nature_guides.models import MetaNode, NatureGuidesTaxonTree, NatureGuide
from app_kit.features.taxon_profiles.models import TaxonProfile, TaxonProfiles
from app_kit.models import ContentImage

from app_kit.appbuilder.JSONBuilders.ContentImagesJSONBuilder import ContentImagesJSONBuilder

import copy

class TaxaBuilder(ContentImagesJSONBuilder):
    
    def __init__(self, app_release_builder):
        
        super().__init__(app_release_builder)
        
        self.meta_app = app_release_builder.meta_app
        taxon_profiles_link = self.meta_app.get_generic_content_links(TaxonProfiles).first()
        self.taxon_profiles = taxon_profiles_link.generic_content
        
        self.gbiflib = GBIFlib()
        
        self.nature_guide_ids = []
        
        self.cache = {
            'simple': {},
            'extended': {},
            'search': {},
            'registry': {},
            'images': {},
        }
    
    
    @property
    def installed_taxonomic_sources(self):
        installed_taxonomic_sources = [s[0] for s in settings.TAXONOMY_DATABASES]
        return installed_taxonomic_sources
    
        
    def serialize_taxon(self, lazy_taxon):
        taxon_serializer = TaxonSerializer(lazy_taxon, self)
        return taxon_serializer.serialize()
    
    
    def serialize_taxon_extended(self, lazy_taxon):
        taxon_serializer = TaxonSerializer(lazy_taxon, self)
        return taxon_serializer.serialize_extended()
    
    def serialize_taxon_with_profile_images(self, lazy_taxon):
        taxon_serializer = TaxonSerializer(lazy_taxon, self)
        return taxon_serializer.serialize_with_profile_images()
    
    
    def serialize_as_search_taxon(self, lazy_taxon, name_type, name, is_preferred_name,
                                  accepted_name_uuid=None):
        taxon_serializer = TaxonSerializer(lazy_taxon, self)
        return taxon_serializer.serialize_as_search_taxon(name_type, name, is_preferred_name,
                                  accepted_name_uuid)
        
    def serialize_as_registry_taxon(self, lazy_taxon, languages, name_type, name, is_preferred_name,
                                  accepted_name_uuid=None):
        taxon_serializer = TaxonSerializer(lazy_taxon, self)
        return taxon_serializer.serialize_as_registry_taxon(languages, name_type, name, is_preferred_name,
                                  accepted_name_uuid)
    
    
    def serialize_taxon_images(self, lazy_taxon):
        taxon_serializer = TaxonSerializer(lazy_taxon, self)
        return taxon_serializer.serialize_images()
    
    
    def get_nature_guide_ids(self):

        if not self.nature_guide_ids:
            nature_guide_links = self.meta_app.get_generic_content_links(NatureGuide)                                         
            self.nature_guide_ids = nature_guide_links.values_list('object_id', flat=True)

        return self.nature_guide_ids
    
    
    def get_nature_guide_occurrences(self, lazy_taxon):
        nature_guide_ids = self.get_nature_guide_ids()
        
        if lazy_taxon.taxon_source in self.installed_taxonomic_sources:

            meta_nodes = MetaNode.objects.filter(
                nature_guide_id__in=nature_guide_ids,
                node_type='result',
                name_uuid = lazy_taxon.name_uuid).values_list('pk', flat=True)

            node_occurrences = NatureGuidesTaxonTree.objects.filter(nature_guide_id__in=nature_guide_ids,
                       meta_node_id__in=meta_nodes).order_by('pk').distinct('pk')

        else:
            node_occurrences = NatureGuidesTaxonTree.objects.filter(nature_guide_id__in=nature_guide_ids,
                        meta_node__node_type='result',
                        taxon_latname=lazy_taxon.taxon_latname,
                        taxon_author=lazy_taxon.taxon_author).order_by('pk').distinct('pk')
            
        return node_occurrences


class TaxonSerializer:

    def __init__(self, lazy_taxon, taxa_builder):
        self.lazy_taxon = lazy_taxon
        self.taxa_builder = taxa_builder
    
    
    def serialize(self):
        
        if self.lazy_taxon.name_uuid in self.taxa_builder.cache['simple']:
            taxon_json = self.taxa_builder.cache['simple'][self.lazy_taxon.name_uuid]
        
        else:
            taxon_json = {
                'taxonLatname' : self.lazy_taxon.taxon_latname,
                'taxonAuthor' : self.lazy_taxon.taxon_author,
                'taxonSource' : self.lazy_taxon.taxon_source,
                'nameUuid' : self.lazy_taxon.name_uuid,
                'taxonNuid' : self.lazy_taxon.taxon_nuid,
            }
            
            self.taxa_builder.cache['simple'][self.lazy_taxon.name_uuid] = taxon_json
        
        taxon_json_copy = copy.deepcopy(taxon_json)
        
        return taxon_json_copy
    
    
    def serialize_with_slugs(self):
        
        taxon_json = self.serialize()
        
        taxon_json.update({
            'slug': self.taxa_builder.app_release_builder.taxon_slugs['taxon_latname'].get(
                taxon_json['nameUuid'], None),
            'localizedSlug': {},
        })
        
        for language_code, vernacular_slugs in self.taxa_builder.app_release_builder.taxon_slugs['vernacular'].items():
            
            taxon_json['localizedSlug'][language_code] = vernacular_slugs.get(
                taxon_json['nameUuid'], None)
            
        return taxon_json
    
    
    def serialize_with_profile_images(self):
        
        taxon_json = self.serialize_with_slugs()
        all_images = self.serialize_images()
        
        primary_image = all_images['primary']
        
        images = []
        
        if all_images['taxonProfileImages']:
            images = all_images['taxonProfileImages']
        elif all_images['primary']:
            images = [all_images['primary']]
            
        taxon_json['images'] = images
        taxon_json['primaryImage'] = primary_image
        
        return taxon_json
        

    def serialize_extended(self):
        
        if self.lazy_taxon.name_uuid in self.taxa_builder.cache['extended']:
            taxon_json = self.taxa_builder.cache['extended'][self.lazy_taxon.name_uuid]
            
        else:
        
            gbif_nubkey = self.taxa_builder.gbiflib.get_nubKey(self.lazy_taxon)
            
            images = self.serialize_images()

            taxon_json = self.serialize()
            
            taxon_json.update({
                'gbifNubkey': gbif_nubkey,
                'image': images['primary'],
                'shortProfile': None,
            })
            
            taxon_profile = self.get_taxon_profile()
            if taxon_profile:
                taxon_json['shortProfile'] = taxon_profile.short_profile
            
            
            self.taxa_builder.cache['extended'][self.lazy_taxon.name_uuid] = taxon_json

        taxon_json_copy = copy.deepcopy(taxon_json)
        
        return taxon_json_copy
    
    def get_taxon_profile(self):
        taxon_profile = None
        
        taxon_profile_qry = TaxonProfile.objects.filter(
            taxon_profiles=self.taxa_builder.taxon_profiles,
            name_uuid=self.lazy_taxon.name_uuid).first()
        
        if taxon_profile_qry and taxon_profile_qry.publication_status != 'draft':
            taxon_profile = taxon_profile_qry
            
        return taxon_profile
        
    
    def serialize_images(self):
        
        if self.lazy_taxon.name_uuid in self.taxa_builder.cache['images']:
            taxon_images = self.taxa_builder.cache['images'][self.lazy_taxon.name_uuid]
        
        else:
                
            collected_content_image_ids = set([])
            collected_image_store_ids = set([])
            
            taxon_profile = self.get_taxon_profile()
            
            taxon_images = {
                'primary': None,
                'taxonProfileImages' : [],
                'nodeImages' : [],
                'taxonImages' : [],
            }
            
            taxon_profile_images = []
            
            if taxon_profile:
                taxon_profile_images = taxon_profile.images().order_by('position')

            for content_image in taxon_profile_images:
                
                image_entry = None

                if content_image.id not in collected_content_image_ids and content_image.image_store.id not in collected_image_store_ids:
                    image_entry = self.taxa_builder.get_image_json(content_image)

                    taxon_images['taxonProfileImages'].append(image_entry)

                    collected_content_image_ids.add(content_image.id)
                    
                if content_image.is_primary == True:
                    
                    if image_entry == None:
                        image_entry = self.taxa_builder.get_image_json(content_image)
                    
                    taxon_images['primary'] = image_entry
                
                if taxon_images['primary'] == None:
                    taxon_images['primary'] = image_entry
            
            
            # images from nature guides
            node_occurrences = self.taxa_builder.get_nature_guide_occurrences(self.lazy_taxon)
            
            for node in node_occurrences:
            
                is_active = True

                if node.additional_data:
                    is_active = node.additional_data.get('is_active', True)

                if is_active == True:
                    
                    node_image = node.meta_node.image()

                    if node_image is not None and node_image.id not in collected_content_image_ids and node_image.image_store.id not in collected_image_store_ids:
                        collected_content_image_ids.add(node_image.id)
                        image_entry = self.taxa_builder.get_image_json(node_image)

                        collected_content_image_ids.add(node_image.id)
                        collected_image_store_ids.add(node_image.image_store.id)

                        taxon_images['nodeImages'].append(image_entry)
                        
                        if taxon_images['primary'] == None:
                            taxon_images['primary'] = image_entry
            
                    
            # get taxonomic images
            content_images_taxon = ContentImage.objects.filter(image_store__taxon_source=self.lazy_taxon.taxon_source,
                                        image_store__taxon_latname=self.lazy_taxon.taxon_latname,
                                        image_store__taxon_author=self.lazy_taxon.taxon_author).exclude(
                                        pk__in=list(collected_content_image_ids))

            #self.app_release_builder.logger.info('Found {0} images for {1}'.format(taxon_images.count(), profile_taxon.taxon_latname))

            for taxon_image in content_images_taxon:

                if taxon_image is not None and taxon_image.id not in collected_content_image_ids and taxon_image.image_store.id not in collected_image_store_ids:

                    image_entry = self.taxa_builder.get_image_json(taxon_image)
                    taxon_images['taxonImages'].append(image_entry)
                    
                    if taxon_images['primary'] == None:
                        taxon_images['primary'] = image_entry

                    collected_content_image_ids.add(taxon_image.id)
                    collected_image_store_ids.add(taxon_image.image_store.id)
    
            self.taxa_builder.cache['images'][self.lazy_taxon.name_uuid] = taxon_images
            
        taxon_images_copy = copy.deepcopy(taxon_images)
        
        return taxon_images_copy
    
    
    def serialize_as_search_taxon(self, name_type, name, is_preferred_name, accepted_name_uuid=None):
        
        if name_type not in self.taxa_builder.cache['search']:
            self.taxa_builder.cache['search'][name_type] = {}
            
        if name in self.taxa_builder.cache['search'][name_type]:
            search_taxon_json = self.taxa_builder.cache['search'][name_type][name]
            
        else:
        
            if not accepted_name_uuid:
                accepted_name_uuid = self.lazy_taxon.name_uuid
                
            has_taxon_profile = False
            taxon_profile = self.get_taxon_profile()
            if taxon_profile:
                has_taxon_profile = True
            
            search_taxon_json = self.serialize_extended()
            
            search_taxon_json.update({
                'nameType': name_type,
                'name': name,
                'isPreferredName': is_preferred_name,
                'acceptedNameUuid': accepted_name_uuid,
                'hasTaxonProfile': has_taxon_profile,
            })
            
            self.taxa_builder.cache['search'][name_type][name] = search_taxon_json
        
        search_taxon_json_copy = copy.deepcopy(search_taxon_json)
        
        return search_taxon_json_copy
    
    
    def serialize_as_registry_taxon(self, languages, name_type, name, is_preferred_name, accepted_name_uuid=None):
        
        if self.lazy_taxon.name_uuid in self.taxa_builder.cache['registry']:
            registry_taxon_json = self.taxa_builder.cache['registry']
            
        else:
        
            registry_taxon_json = self.serialize_as_search_taxon(name_type, name, is_preferred_name, accepted_name_uuid)
            
            registry_taxon_json.update({
                'vernacularNames' : {},
            })
            
            for language_code in languages:
                preferred_vernacular_name = self.lazy_taxon.get_preferred_vernacular_name(language_code,
                                                                            self.taxa_builder.meta_app)
                
                if preferred_vernacular_name:
                    registry_taxon_json['vernacularNames'][language_code] = preferred_vernacular_name
                    
            self.taxa_builder.cache['registry'][self.lazy_taxon.name_uuid] = registry_taxon_json
            
        registry_taxon_json_copy = copy.deepcopy(registry_taxon_json)
        
        return registry_taxon_json_copy
        
    
    def serialize_taxonomic_restriction(self, restriction_type):
        
        taxon_json = self.serialize()
        taxonomic_restriction_json = copy.deepcopy(taxon_json)
        taxonomic_restriction_json['restrictionType'] = restriction_type
        
        return taxonomic_restriction_json

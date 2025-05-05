from django.conf import settings
from localcosmos_server.taxonomy.TaxonManager import (TaxonManager as BaseTaxonManager,
                                                      SWAPPABILITY_CHECK_STATIC_FIELDS)

from django.utils.translation import gettext_lazy as _

from app_kit.models import ContentImage, ImageStore
from app_kit.generic import AppContentTaxonomicRestriction
from app_kit.features.backbonetaxonomy.models import BackboneTaxa
from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonProfile, TaxonProfilesNavigation,
        TaxonProfilesNavigationEntryTaxa)
from app_kit.features.maps.models import Map, FilterTaxon
from app_kit.features.nature_guides.models import NatureGuide, MetaNode
from app_kit.features.generic_forms.models import GenericForm, GenericField
from app_kit.utils import get_content_instance_meta_app

from taxonomy.lazy import LazyTaxon


CUSTOM_TAXONOMY_NAME = 'taxonomy.sources.custom'

'''
- ModelWithRequiredTaxon
    - AppContentTaxonomicRestriction
        - GenericForm
        - GenericField
    - BackboneTaxa
    - FilterTaxon
    - TaxonProfile
    - TaxonProfilesNavigationEntryTaxa
- ModelWithTaxon
    - MetaNode
    - ImageStore
'''

APP_KIT_SUPPORTED_SWAP_MODELS = [AppContentTaxonomicRestriction, BackboneTaxa, FilterTaxon, TaxonProfile,
                                 TaxonProfilesNavigationEntryTaxa, MetaNode, ImageStore]

APP_KIT_SWAPPABILITY_CHECK_STATIC_FIELDS = SWAPPABILITY_CHECK_STATIC_FIELDS.copy()
APP_KIT_SWAPPABILITY_CHECK_STATIC_FIELDS.update({
    'AppContentTaxonomicRestriction': ['content_type', 'object_id'],
    'BackboneTaxa': ['backbonetaxonomy'],
    'FilterTaxon': ['taxonomic_filter__map'],
    'TaxonProfile': ['taxon_profiles'],
    'TaxonProfilesNavigationEntryTaxa': ['navigation_entry'],
    'MetaNode': ['nature_guide'],
    'ImageStore': [],
})

class TaxonManager(BaseTaxonManager):
    
    supported_swap_models = APP_KIT_SUPPORTED_SWAP_MODELS
    # unsupported_swap_models are the same as with the superclass
    swappability_check_static_fields = APP_KIT_SWAPPABILITY_CHECK_STATIC_FIELDS
    
    def __init__(self, meta_app):
        super().__init__(meta_app.app)
        self.meta_app = meta_app
    
    def _get_BackboneTaxa_occurrences(self, occurrence_qry):
        backbonetaxonomy = self.meta_app.backbone()
        occurrence_qry = occurrence_qry.filter(backbonetaxonomy=backbonetaxonomy)
        return occurrence_qry
        
    
    def _get_TaxonProfile_occurrences(self, occurrence_qry):
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        occurrence_qry = occurrence_qry.filter(taxon_profiles=taxon_profiles)
        return occurrence_qry
    
    def _get_TaxonProfilesNavigationEntryTaxa_occurrences(self, occurrence_qry):
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        navigation = TaxonProfilesNavigation.objects.filter(taxon_profiles=taxon_profiles).first()
        
        occurrence_qry = occurrence_qry.filter(navigation_entry__navigation=navigation)
        return occurrence_qry
    
    def _get_FilterTaxon_occurrences(self, occurrence_qry):
        map_links = self.meta_app.get_generic_content_links(Map)
        maps = [map_link.generic_content for map_link in map_links]
        occurrence_qry = occurrence_qry.filter(taxonomic_filter__map__in=maps)
        return occurrence_qry
    
    def _get_MetaNode_occurrences(self, occurrence_qry):
        nature_guide_links = self.meta_app.get_generic_content_links(NatureGuide)
        nature_guides = [nature_guide_link.generic_content for nature_guide_link in nature_guide_links]
        occurrence_qry = occurrence_qry.filter(nature_guide__in=nature_guides)
        return occurrence_qry
    
    
    # has no reference to MetaApp
    def _get_AppContentTaxonomicRestriction_occurrences(self, occurrence_qry):
        matching_occurrences = []
        
        for occurrence in occurrence_qry:
            content_instance = occurrence.content
            
            content_instance_meta_app = get_content_instance_meta_app(content_instance)
            if content_instance_meta_app == self.meta_app:
                matching_occurrences.append(occurrence)
        return matching_occurrences
    
    # has no reference to MetaApp
    def _get_ImageStore_occurrences(self, occurrence_qry):
        
        matching_image_stores = []
        
        for image_store in occurrence_qry:
            content_image = ContentImage.objects.filter(image_store=image_store).first()
            if content_image:
                content_instance = content_image.content
                content_image_app = get_content_instance_meta_app(content_instance)
                if content_image_app == self.meta_app:
                    matching_image_stores.append(image_store)
                    
        return matching_image_stores
    
    
    '''
        methods for getting a human readable name for a taxon occurrence
    '''
    def _get_BackboneTaxa_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = [_('has been manually added to the Backbone Taxonomy')]
        
        verbose_entry = self._get_verbose_entry(model, occurrences, verbose_model_name, verbose_occurrences)
        
        return [verbose_entry]
    
    
    def _get_AppContentTaxonomicRestriction_occurrences_verbose(self,  occurrences_entry):
        return self._get_TaxonomicRestriction_occurrences_verbose(occurrences_entry)
    
    
    def _get_TaxonProfile_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = [_('exists as a Taxon Profile')]
        
        verbose_entry = self._get_verbose_entry(model, occurrences, verbose_model_name, verbose_occurrences)
        
        return [verbose_entry]
    
    
    def _get_TaxonProfilesNavigationEntryTaxa_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = [_('occurs in %(count)s navigation entries') % {'count': len(occurrences)}]
        
        verbose_entry = self._get_verbose_entry(model, occurrences, verbose_model_name, verbose_occurrences)
        
        return [verbose_entry]
    
    def _get_FilterTaxon_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = [_('is a taxonomic filter of Map')]
        
        verbose_entry = self._get_verbose_entry(model, occurrences, verbose_model_name, verbose_occurrences)
        
        return [verbose_entry]
    
    def _get_MetaNode_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_entries = []
        
        for occurrence in occurrences:
            nature_guide = occurrence.nature_guide
            if nature_guide:
                
                verbose_model_name = str(occurrence.nature_guide._meta.verbose_name)
                verbose_occurrences = [_('occurs in Nature Guide %(nature_guide)s') % {'nature_guide': nature_guide.name}]
                
                verbose_entry = self._get_verbose_entry(model, [occurrence], verbose_model_name, verbose_occurrences)
                verbose_entries.append(verbose_entry)
        
        return verbose_entries
    
    def _get_ImageStore_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = []
        
        for occurrence in occurrences:
            
            content_image = ContentImage.objects.filter(image_store=occurrence).first()
            
            content = content_image.content
            verbose_occurrences.append(_('appears as an image of %(content)s (%(model)s)') % {
                'content': str(content),
                'model': str(content._meta.verbose_name),
            })
        
        verbose_entry = self._get_verbose_entry(model, occurrences, verbose_model_name, verbose_occurrences)
        

        return [verbose_entry]
    
    
'''
    this class checks all you app's Taxa and if they are still covered by the taxonomic database
'''
class TaxonReferencesUpdater:
    
    def __init__(self, meta_app):
        self.meta_app = meta_app
        self.taxon_manager = TaxonManager(meta_app)
    
    # check all taxa, but only add one error per taxon
    def check_taxa(self, update=False):
        
        models_with_taxon = self.taxon_manager.get_taxon_models()
        
        result = []
        used_taxa = []
        
        for model in models_with_taxon:
            
            instances = model.objects.filter(taxon_latname__isnull=False)
            
            for instance_with_taxon in instances:
                
                meta_app = get_content_instance_meta_app(instance_with_taxon)
                
                if meta_app == self.meta_app:
                
                    lazy_taxon = LazyTaxon(instance=instance_with_taxon)
                    
                    errors = lazy_taxon.check_with_reference()
                    if errors:
                        
                        updated = False
                        
                        if update and lazy_taxon.reference_taxon:

                            # update the taxon, use both .taxon_nuid and .taxon.taxon_nuid
                            # to ensure its update
                            
                            # reference_taxon can be a synonym, a synonym has no taxon_nuid
                            if hasattr(lazy_taxon.reference_taxon, 'taxon'):
                                taxon_nuid = lazy_taxon.reference_taxon.taxon.taxon_nuid
                            else:
                                taxon_nuid = lazy_taxon.reference_taxon.taxon_nuid
                                
                            
                            instance_with_taxon.name_uuid = lazy_taxon.reference_taxon.name_uuid
                            instance_with_taxon.taxon_nuid = taxon_nuid
                            instance_with_taxon.taxon.name_uuid = lazy_taxon.reference_taxon.name_uuid
                            instance_with_taxon.taxon.taxon_nuid = taxon_nuid
                            instance_with_taxon.save()
                            updated = True
                            
                            lazy_taxon = LazyTaxon(instance=instance_with_taxon)
                        
                        if str(lazy_taxon.name_uuid) not in used_taxa:
                            result.append({
                                'instance': instance_with_taxon,
                                'taxon': lazy_taxon,
                                'errors': errors,
                                'updated': updated,
                            })
                            
                            used_taxa.append(str(lazy_taxon.name_uuid))
        
        return result
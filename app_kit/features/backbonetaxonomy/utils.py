from django.conf import settings
from localcosmos_server.taxonomy.TaxonManager import (TaxonManager as BaseTaxonManager,
                                                      SWAPPABILITY_CHECK_STATIC_FIELDS)

from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from app_kit.models import ContentImage, ImageStore
from app_kit.generic import AppContentTaxonomicRestriction
from app_kit.features.backbonetaxonomy.models import BackboneTaxa, TaxonRelationship
from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonProfile, TaxonProfilesNavigation,
        TaxonProfilesNavigationEntryTaxa)
from app_kit.features.maps.models import Map, FilterTaxon
from app_kit.features.nature_guides.models import NatureGuide, MetaNode
from app_kit.features.generic_forms.models import GenericForm, GenericField
from app_kit.features.object_classes.models import ObjectClasses, ObjectClassTaxon
from app_kit.utils import get_content_instance_meta_app

from taxonomy.lazy import LazyTaxon

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon, ModelWithTaxon
from taxonomy.models import TaxonomyModelRouter
from taxonomy.utils import get_subclasses


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
                                 TaxonProfilesNavigationEntryTaxa, MetaNode, ImageStore, TaxonRelationship,
                                 ObjectClassTaxon]

APP_KIT_SWAPPABILITY_CHECK_STATIC_FIELDS = SWAPPABILITY_CHECK_STATIC_FIELDS.copy()
APP_KIT_SWAPPABILITY_CHECK_STATIC_FIELDS.update({
    'AppContentTaxonomicRestriction': ['content_type', 'object_id'],
    'BackboneTaxa': ['backbonetaxonomy'],
    'TaxonRelationship': ['backbonetaxonomy'],
    'FilterTaxon': ['taxonomic_filter__map'],
    'TaxonProfile': ['taxon_profiles'],
    'TaxonProfilesNavigationEntryTaxa': ['navigation_entry'],
    'MetaNode': ['nature_guide'],
    'ImageStore': [],
    'ObjectClassTaxon': ['object_class'],
})

class TaxonManager(BaseTaxonManager):
    
    supported_swap_models = APP_KIT_SUPPORTED_SWAP_MODELS
    # unsupported_swap_models are the same as with the superclass
    swappability_check_static_fields = APP_KIT_SWAPPABILITY_CHECK_STATIC_FIELDS
    
    def __init__(self, meta_app):
        super().__init__(meta_app.app)
        self.meta_app = meta_app
    
    def _get_BackboneTaxa_occurrences(self, occurrence_qry, lazy_taxon):
        backbonetaxonomy = self.meta_app.backbone()
        occurrence_qry = occurrence_qry.filter(backbonetaxonomy=backbonetaxonomy)
        return occurrence_qry
        
    
    def _get_TaxonProfile_occurrences(self, occurrence_qry, lazy_taxon):
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        occurrence_qry = occurrence_qry.filter(taxon_profiles=taxon_profiles)
        return occurrence_qry
    
    def _get_TaxonProfilesNavigationEntryTaxa_occurrences(self, occurrence_qry, lazy_taxon):
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        navigation = TaxonProfilesNavigation.objects.filter(taxon_profiles=taxon_profiles).first()
        
        occurrence_qry = occurrence_qry.filter(navigation_entry__navigation=navigation)
        return occurrence_qry
    
    def _get_FilterTaxon_occurrences(self, occurrence_qry, lazy_taxon):
        map_links = self.meta_app.get_generic_content_links(Map)
        maps = [map_link.generic_content for map_link in map_links]
        occurrence_qry = occurrence_qry.filter(taxonomic_filter__map__in=maps)
        return occurrence_qry
    
    def _get_MetaNode_occurrences(self, occurrence_qry, lazy_taxon):
        nature_guide_links = self.meta_app.get_generic_content_links(NatureGuide)
        nature_guides = [nature_guide_link.generic_content for nature_guide_link in nature_guide_links]
        occurrence_qry = occurrence_qry.filter(nature_guide__in=nature_guides)
        return occurrence_qry
    
    
    def _get_TaxonRelationship_occurrences(self, occurrence_qry, lazy_taxon):
        backbonetaxonomy = self.meta_app.backbone()
        occurrence_qry = occurrence_qry.filter(backbonetaxonomy=backbonetaxonomy)

        related_taxon_qry = TaxonRelationship.objects.filter(backbonetaxonomy=backbonetaxonomy,
            related_taxon_source=lazy_taxon.taxon_source,
            related_taxon_latname=lazy_taxon.taxon_latname,
            related_taxon_author=lazy_taxon.taxon_author)

        occurrence_qry = occurrence_qry.union(related_taxon_qry)
        return occurrence_qry
    
    
    # has no reference to MetaApp
    def _get_AppContentTaxonomicRestriction_occurrences(self, occurrence_qry, lazy_taxon):
        matching_occurrences = []
        
        for occurrence in occurrence_qry:
            content_instance = occurrence.content
            
            content_instance_meta_app = get_content_instance_meta_app(content_instance)
            if content_instance_meta_app == self.meta_app:
                matching_occurrences.append(occurrence)
        return matching_occurrences
    
    # has no reference to MetaApp
    def _get_ImageStore_occurrences(self, occurrence_qry, lazy_taxon):
        
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
    
    
    def _get_TaxonRelationship_occurrences_verbose(self, occurrences_entry):
        
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = [_('is used in %(count)s taxon relationship(s)') % {'count': len(occurrences)}]
        
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
    
    def _get_ObjectClassTaxon_occurrences(self, occurrence_qry, lazy_taxon):
        object_classes_links = self.meta_app.get_generic_content_links(ObjectClasses)
        all_object_classes = [link.generic_content for link in object_classes_links]
        occurrence_qry = occurrence_qry.filter(object_class__object_classes__in=all_object_classes)
        return occurrence_qry

    def _get_ObjectClassTaxon_occurrences_verbose(self, occurrences_entry):
        occurrences = occurrences_entry['occurrences']
        model = occurrences_entry['model']
        verbose_model_name = str(model._meta.verbose_name)
        verbose_occurrences = [_('occurs in %(count)s object class taxon mappings') % {'count': len(occurrences)}]
        verbose_entry = self._get_verbose_entry(model, occurrences, verbose_model_name, verbose_occurrences)
        return [verbose_entry]

    # support for swapping related_taxon
    def _swap_taxon_TaxonRelationship(self, lazy_taxon, new_lazy_taxon):
        
        # swap TaxonRelationship.taxon
        self.perform_swap(TaxonRelationship, lazy_taxon, new_lazy_taxon)
        
        # swap TaxonRelationship.related_taxon
        backbonetaxonomy = self.meta_app.backbone()

        occurrences = TaxonRelationship.objects.filter(backbonetaxonomy=backbonetaxonomy,
            related_taxon_source=lazy_taxon.taxon_source, related_taxon_latname=lazy_taxon.taxon_latname)
        
        for occurrence in occurrences:
            occurrence.set_related_taxon(new_lazy_taxon)
            occurrence.save()
    
    
'''
    this class checks all you app's Taxa and if they are still covered by the taxonomic database
'''
class TaxonReferencesUpdater:

    def __init__(self, meta_app, custom_taxonomy_only=False):
        self.meta_app = meta_app
        self.taxon_manager = TaxonManager(meta_app)
        self.custom_taxonomy_only = custom_taxonomy_only
    def update_all_taxon_nuid_and_name_uuid_only(self):
        self.check_taxa(update=True)

    def check_taxa(self, update=False):
        models_with_taxon = self.taxon_manager.get_taxon_models()
        errors = []
        self._total_taxa_checked = 0
        checked_taxa_cache = {}  # cache reference check results by taxon identity key

        for model in models_with_taxon:
            instances = model.objects.filter(taxon_latname__isnull=False)
            for instance_with_taxon in instances:
                meta_app = get_content_instance_meta_app(instance_with_taxon)
                if meta_app != self.meta_app:
                    continue

                lazy_taxon = LazyTaxon(instance=instance_with_taxon)

                if self.custom_taxonomy_only and lazy_taxon.taxon_source != CUSTOM_TAXONOMY_NAME:
                    continue

                cache_key = (lazy_taxon.taxon_source, lazy_taxon.taxon_latname,
                             lazy_taxon.taxon_author, str(lazy_taxon.name_uuid), lazy_taxon.taxon_nuid)

                if cache_key in checked_taxa_cache:
                    checked_taxon = checked_taxa_cache[cache_key]
                else:
                    lazy_taxon.check_with_reference()
                    checked_taxa_cache[cache_key] = lazy_taxon
                    checked_taxon = lazy_taxon

                self._total_taxa_checked += 1

                if len(checked_taxon.reference_errors) == 0:
                    continue

                updated = False
                result_taxon = checked_taxon

                if update and checked_taxon.exists_as_taxon_in_reference and checked_taxon.reference_taxon:
                    
                    if checked_taxon.changed_taxon_nuid_in_reference or checked_taxon.changed_name_uuid_in_reference:
                        
                        ref = checked_taxon.reference_taxon
                        if hasattr(ref, 'taxon'):
                            taxon_nuid = ref.taxon.taxon_nuid
                            name_uuid = ref.name_uuid
                        else:
                            taxon_nuid = ref.taxon_nuid
                            name_uuid = ref.name_uuid

                        type(instance_with_taxon).objects.filter(pk=instance_with_taxon.pk).update(
                            taxon_nuid=taxon_nuid,
                            name_uuid=name_uuid,
                        )

                        instance_with_taxon.refresh_from_db()
                        result_taxon = LazyTaxon(instance=instance_with_taxon)
                        
                        updated = True

                errors.append({
                    'instance': instance_with_taxon,
                    'taxon': result_taxon,
                    'errors': list(checked_taxon.reference_errors),
                    'updated': updated,
                })

        return errors


    
    
def check_taxon_parameter_changes():
    changed = []
    def source_taxon(taxon):
        models = TaxonomyModelRouter(taxon.taxon_source)
        tree = models.TaxonTreeModel.objects.filter(name_uuid=taxon.name_uuid).first()
        if tree:
            return tree
        query = models.TaxonTreeModel.objects.filter(taxon_latname=taxon.taxon_latname)
        if taxon.taxon_author:
            query = query.filter(taxon_author=taxon.taxon_author)
        else:
            query = query.filter(Q(taxon_author='',) | Q(taxon_author=None))
        return query.first()
    for base in (ModelWithRequiredTaxon, ModelWithTaxon):
        for Subclass in get_subclasses(base):
            for taxon in Subclass.objects.filter(taxon_latname__isnull=False).iterator():
                ref = source_taxon(taxon)
                if not ref:
                    changed.append((Subclass.__name__, taxon.pk, 'missing'))
                    continue
                diffs = {}
                for field in ('taxon_nuid', 'taxon_latname', 'name_uuid'):
                    if str(getattr(taxon, field)) != str(getattr(ref, field)):
                        diffs[field] = (getattr(taxon, field), getattr(ref, field))
                if diffs:
                    changed.append((Subclass.__name__, taxon.pk, diffs))
    return changed
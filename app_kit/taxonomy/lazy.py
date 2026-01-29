from taxonomy.models import TaxonomyModelRouter, MetaVernacularNames

from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models import Q

TAXON_SOURCES = {
    'app_kit.features.nature_guides': _('Nature Guide'),
}

for source in settings.TAXONOMY_DATABASES:
    if source[0] not in TAXON_SOURCES:
        TAXON_SOURCES[source[0]] = source[1]

from localcosmos_server.taxonomy.lazy import LazyTaxonBase


REFERENCE_ERROR_TYPES = {
    'not_found': 'not_found',
    'multiple_found': 'multiple_found',
    'position_changed': 'position_changed',
    'identifier_changed': 'identifier_changed',
}


class LazyTaxon(LazyTaxonBase):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # set the correct model classes from self.source
        if self.taxon_source in TAXON_SOURCES:
            self.models = TaxonomyModelRouter(self.taxon_source)
            
        self.checked_with_reference = False


    def exists_in_tree(self):
        instance = self.tree_instance()
        if instance:
            return True
        return False

    '''
    the tree instance can be none, if the taxon does not exist anymore in the tree
    - preferrably do NOT query by name_uuid
    - DO query taxon_latname AND taxon_author
    '''
    def tree_instance(self):
        query = self.models.TaxonTreeModel.objects.filter(taxon_latname=self.taxon_latname,
                                                             taxon_author=self.taxon_author)

        if query.count() == 1:
            return query.first()

        else:
            instance = self.models.TaxonTreeModel.objects.filter(name_uuid=self.name_uuid).first()

            if instance:
                return instance

        return None
    
    
    def _get_lookup_query(self, model):
        
        query = model.objects.filter(taxon_latname=self.taxon_latname)
        
        if self.taxon_author:
            query = query.filter(taxon_author=self.taxon_author)
        else:
            # query for author null and empt string '' using django Q.OR
            query = query.filter(Q(taxon_author='') | Q(taxon_author=None))
            
        return query
    
    # TaxonTreeModel or TaxonSynonymModel    
    def check_with_reference(self):
        
        # these should be available only after checking with reference
        self.checked_with_reference = True
        
        self.reference_taxon = None
        self.reference_synonym = None
        self.reference_accepted_name = None
        
        self.reference_errors = []
        
        self.exists_as_synonym_in_reference = False
        self.exists_as_taxon_in_reference = False
        
        self.changed_taxon_nuid_in_reference = False
        self.changed_name_uuid_in_reference = False
        
        self.reference_taxa_with_similar_taxon_latname = []
        self.taxon_source_is_available = True
        
        if self.taxon_source not in TAXON_SOURCES:
            self.taxon_source_is_available = False
            self.reference_errors.append(_('Taxon source %s is not installed') % self.taxon_source)
        
        else:
            verbose_taxon_source = TAXON_SOURCES[self.taxon_source]
            tree_model = self.models.TaxonTreeModel

            tree_query = self._get_lookup_query(tree_model)
            
            if tree_query.exists():
                self.exists_as_taxon_in_reference = True
                taxon = tree_query.first()
                db_lazy_taxon = LazyTaxon(instance=taxon)
                self.reference_taxon = db_lazy_taxon
                
                if db_lazy_taxon.taxon_nuid != self.taxon_nuid:
                    self.changed_taxon_nuid_in_reference = True
                    self.reference_errors.append(_('Taxon %(taxon)s has changed its position in %(tree)s') % {'taxon': self, 'tree': verbose_taxon_source})
        
                if str(taxon.name_uuid) != str(self.name_uuid):
                    self.changed_name_uuid_in_reference = True
                    self.reference_errors.append(_('Taxon %(taxon)s has changed its identifier in %(tree)s') % {'taxon': self, 'tree': verbose_taxon_source})
                    
                if tree_query.count() > 1:
                    self.reference_errors.append(_('Taxon %(taxon)s  found multiple times in %(tree)s') % {'taxon': self, 'tree': verbose_taxon_source})
                    
            else:
                synonyms_model = self.models.TaxonSynonymModel
                synonyms_query = self._get_lookup_query(synonyms_model)
                
                if synonyms_query.exists():
                    self.exists_as_synonym_in_reference = True
                    synonym = synonyms_query.first()
                    
                    self.reference_synonym = synonym
                    accepted_name = synonym.taxon
                    self.reference_accepted_name = LazyTaxon(instance=accepted_name)
                    self.reference_errors.append(_('Taxon %(taxon)s not found as accepted name, but as synonym of %(accepted_name)s') % {'taxon': self,
                            'accepted_name': accepted_name})
                    
                else:
                    self.reference_errors.append(_('Taxon %(taxon)s not found in %(tree)s') % {'taxon': self, 'tree': verbose_taxon_source})
                    
                
                taxon_latnames_query = self.models.TaxonTreeModel.objects.filter(
                    taxon_latname__iexact=self.taxon_latname)
                self.reference_taxa_with_similar_taxon_latname = taxon_latnames_query.all()
        

    def synonyms(self):
        tree_instance = self.tree_instance()
        synonyms = []
        
        if tree_instance:
            synonyms = self.models.TaxonSynonymModel.objects.filter(taxon=tree_instance)

        return synonyms


    def exists_as_synonym(self):
        instance = self.synonym_instance()
        if instance:
            return True
        return False

        
    def synonym_instance(self):
        query = self.models.TaxonSynonymModel.objects.filter(taxon_latname=self.taxon_latname,
                                                             taxon_author=self.taxon_author)

        if query.count() == 1:
            return query.first()

        else:
            instance = self.models.TaxonSynonymModel.objects.filter(name_uuid=self.name_uuid).first()

            if instance:
                return instance

        return None


    def preferred_name_lazy_taxon(self):
        synonym_instance = self.synonym_instance()
        tree_instance = self.tree_instance()

        if tree_instance:
            return self

        elif synonym_instance:
            lazy_taxon = LazyTaxon(instance=synonym_instance.taxon)
            return lazy_taxon

        return None
    
    '''
        vernacular names
    '''    
    def get_taxon_source_vernacular_name(self, language):
        
        vernacular_name = None
        
        locale = self.models.TaxonLocaleModel.objects.filter(taxon=self.name_uuid,
            language=language, preferred=True).first()
        
        if not locale:
            self.models.TaxonLocaleModel.objects.filter(taxon=self.name_uuid,
                language=language).first()
            
        if not locale:
            locale = self.models.TaxonLocaleModel.objects.filter(taxon=self.name_uuid).first()
            
        if locale:
            vernacular_name = locale.name
            
        return vernacular_name
            
    
    '''
        1.: preferred name in MetaVernacularNames
        2.: first name in MetaVernacularNames
        2.: first name of occurrence in NatureGuide (if translation exists)
        3.: preferred name in taxonomy_database.models.TaxonLocale
        4.: first name in taxonomy_database.models.TaxonLocale
    '''
    def get_preferred_vernacular_name(self, language, meta_app=None):
        preferred_vernacular_name = None
        
        meta_vernacular_names = MetaVernacularNames.objects.filter(taxon_source=self.taxon_source,
                                                                   name_uuid=self.name_uuid)
        
        if meta_vernacular_names:
            preferred_meta_vernacular_name = meta_vernacular_names.filter(preferred=True).first()
            
            if preferred_meta_vernacular_name:
                preferred_vernacular_name = preferred_meta_vernacular_name.name
        
            if not preferred_vernacular_name:
                meta_vernacular_name = meta_vernacular_names.first()
                preferred_vernacular_name = meta_vernacular_name.name
        
        if not preferred_vernacular_name and self.taxon_source == 'taxonomy.sources.custom':
            preferred_vernacular_name = self.get_taxon_source_vernacular_name(language)

        if not preferred_vernacular_name and meta_app:
            primary_locale_vernacular_name = self.get_primary_locale_vernacular_name_from_nature_guides(meta_app)
            if language == meta_app.primary_language:
                preferred_vernacular_name = primary_locale_vernacular_name
            else:
                localization = self.meta_app.localizations.get(language, {})
                preferred_vernacular_name = localization.get(primary_locale_vernacular_name, None)
                
        if not preferred_vernacular_name:
            preferred_vernacular_name = self.get_taxon_source_vernacular_name(language)
            
        return preferred_vernacular_name
        
        
    def vernacular(self, language=None, cache=None, meta_app=None):

        if cache:
            if self.taxon_source in cache and self.name_uuid in cache[self.taxon_source]:

                cache_entry = cache[self.taxon_source][self.name_uuid]

                if language in cache_entry:
                    return cache_entry[language]

                return None

        if language == None:
            if meta_app:
                language = meta_app.primary_language
            else:
                language = translation.get_language()[:2].lower()

        # first use the MetaVernacularNames
        preferred_vernacular_name = self.get_preferred_vernacular_name(language, meta_app)
        
        if preferred_vernacular_name:
            return preferred_vernacular_name

        if self.origin == 'MetaNode':
            return self.instance.name
            
        return None
    

    def _get_vernacular_name_reference(self, name, language, is_preferred_name, instance):
        
        origin = instance.__class__.__name__
        verbose_origin = instance._meta.verbose_name
        
        if isinstance(instance, MetaVernacularNames):
            verbose_origin = _('manually added')

        
        vernacular_reference = {
            'name': name,
            'language': language,
            'is_preferred_name': is_preferred_name,
            'instance': instance,
            'origin': origin,
            'verbose_origin': verbose_origin,
        }
        
        return vernacular_reference
    
    
    def all_vernacular_names(self, meta_app, distinct=True, only_preferred=False, languages=[]):
        
        names = []
        used_names = []
        
        preferred_vernacular_name = None
        
        meta_vernacular_names = MetaVernacularNames.objects.filter(taxon_source=self.taxon_source,
                                                                   name_uuid=self.name_uuid)
        
        if languages:
            meta_vernacular_names = meta_vernacular_names.filter(language__in=languages)
            
        if only_preferred == True:
            meta_vernacular_names = meta_vernacular_names.filter(preferred=True)

        
        for mvn in meta_vernacular_names:
            
            if mvn.name in used_names and distinct == True:
                continue
            
            is_preferred = False
            if mvn.preferred and not preferred_vernacular_name:
                preferred_vernacular_name = mvn.name
                is_preferred = True
            
            used_names.append(mvn.name)
            
            vernacular_name_reference = self._get_vernacular_name_reference(mvn.name, mvn.language,
                                                                            is_preferred, mvn)
            
            names.append(vernacular_name_reference)
            
            
        vernacular_meta_nodes = self.get_vernacular_meta_nodes(meta_app)
        if vernacular_meta_nodes:
            
            for meta_node in vernacular_meta_nodes:
                if meta_node.name not in used_names:
                    ng_name_reference = self._get_vernacular_name_reference(meta_node.name,
                                                        meta_app.primary_language, False, meta_node)
                    names.append(ng_name_reference)
            
        
        taxon_locales = self.models.TaxonLocaleModel.objects.filter(taxon=self.name_uuid)
        
        if languages:
            taxon_locales = taxon_locales.filter(language__in=languages)
        if only_preferred == True:
            taxon_locales = taxon_locales.filter(preferred=True)

        for taxon_locale in taxon_locales:
            
            if taxon_locale.name in used_names and distinct == True:
                continue
            
            is_preferred = False
            
            if taxon_locale.preferred and not preferred_vernacular_name:
                preferred_vernacular_name = taxon_locale.name
                is_preferred = True
            
            used_names.append(taxon_locale.name)
            vernacular_name_reference = self._get_vernacular_name_reference(taxon_locale.name,
                                        taxon_locale.language, is_preferred, taxon_locale)
            
            names.append(vernacular_name_reference)
            
        return names
        
    def get_vernacular_meta_nodes(self, meta_app):
        
        from app_kit.features.nature_guides.models import NatureGuide, MetaNode
        installed_taxonomic_sources = [s[0] for s in settings.TAXONOMY_DATABASES]

        if self.taxon_source in installed_taxonomic_sources:

            nature_guide_links = meta_app.get_generic_content_links(NatureGuide)
            nature_guide_ids = nature_guide_links.values_list('object_id', flat=True)

            meta_nodes = MetaNode.objects.filter(nature_guide_id__in=nature_guide_ids,
                name_uuid=self.name_uuid)

            return meta_nodes
        
        return []
            

    def get_primary_locale_vernacular_name_from_nature_guides(self, meta_app):
        
        meta_nodes = self.get_vernacular_meta_nodes(meta_app)
        
        if meta_nodes:
            meta_node = meta_nodes.first()
            return meta_node.name
        
        return None
        

    def descendants(self):
        return self.models.TaxonTreeModel.objects.filter(taxon_nuid__startswith=self.taxon_nuid)
    
    
    def get_taxonomic_branch(self):
        
        branch = []
        tree_instance = self.tree_instance()
        
        if tree_instance:
            
            parent = tree_instance.parent
            
            while parent:
                branch.append(parent)
                parent = parent.parent
        
        branch.reverse()
        return branch


from localcosmos_server.taxonomy.lazy import LazyTaxonListBase

class LazyTaxonList(LazyTaxonListBase):
    LazyTaxonClass = LazyTaxon

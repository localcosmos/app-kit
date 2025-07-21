from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

# prevent caching of large queries
from app_kit.server_side_cursors import server_side_cursors
from taxonomy.lazy import LazyTaxon

from django.template.defaultfilters import slugify 



'''
    App Backbone Taxonomy builder
    - latnames are stored as alphabetical files, e.g. AA.json
    - vernacular names are stored as alphabetical files, e.g. AA.json
    - vernacular names are also fetched from the nature guide, the taxonomic source is the nature guide itself
      if no taxon is assigned
'''
class BackboneTaxonomyJSONBuilder(JSONBuilder):

    def build(self):
        return self._build_common_json()


    # Search indices are meant for searching taxa, not alphabetical display
    # the same taxon can have multiple names and therefore occur more than once in the index
    # one file per letter is used: A.json, B.json and so on
    def build_taxon_latname_search_index(self):
        
        search_index = {}
        
        higher_taxa = self.meta_app.higher_taxa(include_draft_contents=False)
        
        for start_letter, taxon_json in self._work_taxon_latname_search_querysets(higher_taxa.querysets):
            if start_letter not in search_index:
                search_index[start_letter] = []
                
            search_index[start_letter].append(taxon_json)
                
        taxa = self.meta_app.taxa(include_draft_contents=False)

        for start_letter, taxon_json in self._work_taxon_latname_search_querysets(taxa.querysets):
            if start_letter not in search_index:
                search_index[start_letter] = []
                
            search_index[start_letter].append(taxon_json)
       
                
        return search_index
    
    
    def _work_taxon_latname_search_querysets(self, querysets):
        
        used_name_uuids = set([])
        
        for queryset in querysets:
            
            for taxon_instance in queryset:

                lazy_taxon = LazyTaxon(instance=taxon_instance)
                
                name_uuid = str(lazy_taxon.name_uuid)
                
                if name_uuid not in used_name_uuids:
                    
                    used_name_uuids.add(name_uuid)
                    
                    full_scientific_name = str(lazy_taxon)
                    taxon_latname_search_taxon = self.app_release_builder.taxa_builder.serialize_as_search_taxon(
                        lazy_taxon, 'scientific', full_scientific_name, True)
            
                    start_letter = lazy_taxon.taxon_latname[0].upper()
                    
                    yield start_letter, taxon_latname_search_taxon
                    
                    # add synonyms
                    synonyms = lazy_taxon.synonyms()
                    for synonym in synonyms:
                        
                        lazy_synonym_kwargs = {
                            'taxon_source': lazy_taxon.taxon_source,
                            'taxon_latname': synonym.taxon_latname,
                            'taxon_author': synonym.taxon_author,
                            'name_uuid': str(synonym.name_uuid),
                            'taxon_nuid': lazy_taxon.taxon_nuid,
                        }
                        
                        lazy_synonym = LazyTaxon(**lazy_synonym_kwargs)
                        
                        full_synonym_name = str(lazy_synonym)
                        
                        synonym_search_taxon = self.app_release_builder.taxa_builder.serialize_as_search_taxon(
                            lazy_synonym, 'scientific', full_synonym_name, False, accepted_name_uuid=name_uuid)
            
                        synonym_start_letter = lazy_synonym.taxon_latname[:1].upper()
                    
                        yield synonym_start_letter, synonym_search_taxon
        
    
    def build_vernacular_search_index(self, language_code):
        
        vernacular_index = {}
        vernacular_lookup = {}
        
        taxa = self.meta_app.taxa(include_draft_contents=False)
        
        worked_taxon_uuids = set([])
        
        for taxon_instance in taxa:
            
            if taxon_instance.name_uuid in worked_taxon_uuids:
                continue
            
            worked_taxon_uuids.add(taxon_instance.name_uuid)
            
            existing_names = []
            
            lazy_taxon = LazyTaxon(instance=taxon_instance)
            
            vernacular_lookup[lazy_taxon.name_uuid] = {
                'primary': lazy_taxon.vernacular(language=language_code, meta_app=self.meta_app),
                'secondary': []
            }
        
            vernacular_names = lazy_taxon.all_vernacular_names(self.meta_app, languages=[language_code])
            
            for name_reference in vernacular_names:
                
                name = name_reference['name']
                
                if name in existing_names:
                    continue
                
                existing_names.append(name)
                
                if name != vernacular_lookup[lazy_taxon.name_uuid]['primary'] and name not in vernacular_lookup[lazy_taxon.name_uuid]['secondary']:
                    vernacular_lookup[lazy_taxon.name_uuid]['secondary'].append(name)
                
                start_letter = name[0].upper()
                
                if start_letter not in vernacular_index:
                    vernacular_index[start_letter] = []
                    
                search_taxon = self.app_release_builder.taxa_builder.serialize_as_search_taxon(
                    lazy_taxon, 'vernacular', name, name_reference['is_preferred_name'])
                
                vernacular_index[start_letter].append(search_taxon)
        
        return vernacular_index, vernacular_lookup
    
    
    def build_slugs(self, languages=[]):
        
        taxa = self.meta_app.taxa(include_draft_contents=False)
        
        # taxon latname slugs
        slugs = {}
        
        # vernacular slugs
        localized_slugs = {}
        
        for taxon in taxa:
            lazy_taxon = LazyTaxon(instance=taxon)
            
            name = slugify(taxon.taxon_latname)
        
            slug = name
            
            if slug in slugs and slugs[slug] == str(taxon.name_uuid):
                continue
            
            counter = 2
            
            while slug in slugs:
                slug = '{0}-{1}'.format(name, counter)
                counter = counter +1
                
            slugs[slug] = str(taxon.name_uuid)
            
            for language_code in languages:
                
                if language_code not in localized_slugs:
                    localized_slugs[language_code] = {}
                
                vernacular_name = lazy_taxon.vernacular(language=language_code,
                                                                meta_app=self.meta_app)
                
                if vernacular_name:
                    
                    slug_base = slugify(vernacular_name)
                    vernacular_slug = slug_base
                    
                    if vernacular_slug in localized_slugs[language_code] and localized_slugs[language_code][vernacular_slug] == str(taxon.name_uuid):
                        continue
                    
                    while vernacular_slug in localized_slugs[language_code]:
                        vernacular_slug = '{0}-{1}'.format(slug_base, counter)
                        counter = counter +1
                        
                    localized_slugs[language_code][vernacular_slug] = str(taxon.name_uuid)
   
        
        return slugs, localized_slugs
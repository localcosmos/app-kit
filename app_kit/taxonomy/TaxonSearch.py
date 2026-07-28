"""
    a class managing all taxa across different sources
    the search depends on a selected source

    in the end, this should use a NAMES view, not TaxonTree and TaxonLocale models
"""

from django.db.models import Q

from .models import TaxonomyModelRouter

from .lazy import LazyTaxon

class TaxonSearch(object):

    def __init__(self, taxon_source, searchtext, language, *args, **kwargs):

        self.limit = kwargs.get('limit', 10)
        self.min_length = kwargs.get('min_length', 3)

        self.language = language.lower()
        self.taxon_source = taxon_source
        self.searchtext = searchtext.replace('+',' ').upper().strip()

        # get the models from the source
        self.models = TaxonomyModelRouter(taxon_source)
        
        self.latnames_query = []
        self.names_query = []
        self.exact_latnames_query = []
        self.exact_names_query = []
        
        self.queries_ready = False

        self.kwargs = kwargs


    def make_custom_queries(self):

        self.exact_matches_query = self.models.TaxonTreeModel.objects.filter(
            taxon_latname__iexact=self.searchtext.upper())

        self.matches_query = self.models.TaxonTreeModel.objects.filter(
            taxon_latname__istartswith=self.searchtext.upper())

        self.vernacular_query = self.models.TaxonLocaleModel.objects.filter(
            language=self.language, name__icontains=self.searchtext.upper())

    # do not apply limits here, because queries cannot be filtered after slicing
    def make_queries(self):

        if self.taxon_source == 'taxonomy.sources.custom':
            self.make_custom_queries()

        else:

            self.exact_matches_query = self.models.TaxonNamesModel.objects.filter(
                language__in=['la', self.language], name__iexact=self.searchtext.upper())

            self.matches_query = self.models.TaxonNamesModel.objects.filter(
                language__in=['la', self.language], name__istartswith=self.searchtext.upper())

            self.vernacular_query = self.models.TaxonNamesModel.objects.filter(
                language=self.language, name__icontains=self.searchtext.upper())

        self.queries_ready = True
        

    def get_choices_for_typeahead(self):

        if not self.queries_ready:
            self.make_queries()


        names = list(self.exact_matches_query[:5]) + list(self.matches_query[:self.limit]) + list(self.vernacular_query[:self.limit])
        
        choices = []

        for name in names:

            # CustomTaxonLocale has no attribute taxon_latname
            if self.taxon_source == 'taxonomy.sources.custom' and name.__class__.__name__ == 'CustomTaxonLocale':
                taxon = name.taxon
            else:
                taxon = name

            taxon_kwargs = {
                'taxon_source' : self.taxon_source,
                'taxon_latname' : taxon.taxon_latname,
                'taxon_author' : taxon.taxon_author,
                'taxon_nuid' : taxon.taxon_nuid,
                'name_uuid' : taxon.name_uuid,
            }
            
            lazy_taxon = LazyTaxon(**taxon_kwargs)

            if self.taxon_source == 'taxonomy.sources.custom':

                if name.__class__.__name__ == 'CustomTaxonLocale':
                    label = '{0} ({1})'.format(name.name, taxon.taxon_latname)
                else:
                    label = taxon.taxon_latname

            else:

                if name.name_type == 'accepted name':

                    if name.taxon_author:
                        label = '{0} {1}'.format(name.name, name.taxon_author)
                    else:
                        label = '{0}'.format(name.name)
                
                elif name.name_type == 'synonym':
                    if name.taxon_author:
                        label = '{0} {1} [syn. {2}]'.format(name.taxon_latname, name.taxon_author, name.name)
                    else:
                        label = '{0} [syn. {1}]'.format(name.taxon_latname, name.name)
                    
                elif name.name_type == 'vernacular':
                    label = '{0} ({1})'.format(name.name, name.taxon_latname)

            obj = lazy_taxon.as_typeahead_choice(label=label)
                
            if obj not in choices:
                choices.append(obj)

        return choices

    def get_matching_taxon_name_uuids(self):
        """
        Return a set of accepted-taxon name_uuids whose scientific or vernacular names
        match the search text. Suitable for filtering model querysets on name_uuid.
        """
        if not self.queries_ready:
            self.make_queries()

        uuids = set()

        if self.taxon_source == 'taxonomy.sources.custom':
            # exact_matches_query / matches_query are TaxonTreeModel rows
            uuids.update(self.exact_matches_query.values_list('name_uuid', flat=True))
            uuids.update(self.matches_query.values_list('name_uuid', flat=True))
            # vernacular_query is TaxonLocaleModel; taxon_id is FK → TaxonTree.name_uuid
            uuids.update(self.vernacular_query.values_list('taxon_id', flat=True))
        else:
            # TaxonNamesView rows: name_uuid is per-name (not per taxon).
            # taxon_nuid reliably identifies the accepted taxon.
            nuids = set()
            nuids.update(self.exact_matches_query.values_list('taxon_nuid', flat=True))
            nuids.update(self.matches_query.values_list('taxon_nuid', flat=True))
            nuids.update(self.vernacular_query.values_list('taxon_nuid', flat=True))
            uuids.update(
                self.models.TaxonTreeModel.objects.filter(
                    taxon_nuid__in=nuids
                ).values_list('name_uuid', flat=True)
            )

        return uuids

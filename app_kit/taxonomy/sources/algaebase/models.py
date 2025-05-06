from django.db import models

from taxonomy.models import TaxonTree, TaxonSynonym, TaxonNamesView, TaxonLocale


class AlgaebaseTaxonTree(TaxonTree):
    pass


class AlgaebaseTaxonSynonym(TaxonSynonym):
    taxon = models.ForeignKey(AlgaebaseTaxonTree, on_delete=models.CASCADE, to_field='name_uuid')

    class Meta:
        unique_together = ('taxon', 'taxon_latname', 'taxon_author')


class AlgaebaseTaxonLocale(TaxonLocale):
    taxon = models.ForeignKey(AlgaebaseTaxonTree, on_delete=models.CASCADE, to_field='name_uuid')

    class Meta:
        indexes = [
            models.Index(fields=['taxon', 'language']),
        ]
    

'''
    VIEWS
'''
class AlgaebaseTaxonNamesView(TaxonNamesView):
    pass


from django.db import models
from django.utils.translation import gettext_lazy as _

'''
    enable the Catalogue Of Life
    all LocalCosmos enabled taxonomic dbs need 4 models:
    - *TaxonTree
    - *TaxonLocale
    - *TaxonNuid
    - *TaxonNamesView

    plus one TaxonDBManager.py file
'''
from taxonomy.models import TaxonTree, TaxonSynonym, TaxonNamesView, TaxonLocale


class ColTaxonTree(TaxonTree):
    
    class Meta:
        verbose_name = 'Catalogue of Life'


class ColTaxonSynonym(TaxonSynonym):
    taxon = models.ForeignKey(ColTaxonTree, on_delete=models.CASCADE, to_field='name_uuid')

    class Meta:
        unique_together = ('taxon', 'taxon_latname', 'taxon_author')


class ColTaxonLocale(TaxonLocale):
    taxon = models.ForeignKey(ColTaxonTree, on_delete=models.CASCADE, to_field='name_uuid')

    class Meta:
        indexes = [
            models.Index(fields=['taxon', 'language']),
        ]
        
        verbose_name = _('Catalogue of Life')
    

'''
    VIEWS
'''
class ColTaxonNamesView(TaxonNamesView):
    pass


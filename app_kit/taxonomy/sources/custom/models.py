from django.db import models
from taxonomy.utils import NuidManager

"""
    Taxon classes for taxa created and defined by the user
"""
from taxonomy.models import TaxonTree, TaxonSynonym, TaxonNamesView, TaxonLocale, TaxonTreeManager

import uuid

class CustomTaxonTreeManager(TaxonTreeManager):

    def create(self, taxon_latname, taxon_author, **extra_fields):

        source_id = str(uuid.uuid4())
        
        nuidmanager = NuidManager()
        
        parent = extra_fields.get('parent', None)
        last_sibling = None
        
        if parent:
            parent_nuid = parent.taxon_nuid
            children_nuid_length = len(parent_nuid) + 3

            last_sibling = CustomTaxonTree.objects.filter(taxon_nuid__startswith=parent_nuid,
                taxon_nuid__length=children_nuid_length).order_by('taxon_nuid').last()
        else:
            parent_nuid = ''
            # it is a new root_taxon
            last_sibling = CustomTaxonTree.objects.filter(
                is_root_taxon=True).order_by('id').last()
            
        # create the nuid
        if last_sibling:
            nuid = nuidmanager.next_nuid(last_sibling.taxon_nuid)
        else:
            nuid = '{0}{1}'.format(parent_nuid, nuidmanager.decimal_to_nuid(1))
        
        instance = super().create(nuid, taxon_latname, taxon_author, source_id, **extra_fields)

        return instance


class CustomTaxonTree(TaxonTree):
    
    objects = CustomTaxonTreeManager()
    
    class Meta:
        verbose_name = 'Custom Taxonomy'


class CustomTaxonSynonym(TaxonSynonym):
    taxon = models.ForeignKey(CustomTaxonTree, on_delete=models.CASCADE, to_field='name_uuid')

    class Meta:
        unique_together = ('taxon', 'taxon_latname', 'taxon_author')


class CustomTaxonLocale(TaxonLocale):
    taxon = models.ForeignKey(CustomTaxonTree, on_delete=models.CASCADE, to_field='name_uuid')

    class Meta:
        unique_together = ('taxon', 'language', 'name')


class CustomTaxonNamesView(TaxonTree):
    
    objects = CustomTaxonTreeManager()

    class Meta:
        managed = False
        db_table = 'custom_customtaxontree'

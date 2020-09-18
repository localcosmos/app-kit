'''
    GLOSSARY FEATURE
    - available in the app after build
    - the build process adds an image with link after a recognized term
    - eg: the term "leaf" has been recognized in the locale entry "green Leaf"
      the transation will be something like "green Leaf<a href="glossary?term=leaf" class="glossarylink"><img src="glossarylinkimage.jpg" /></a>"
'''

from django.db import models
from django.utils.translation import gettext_lazy as _

from app_kit.generic import GenericContent
from taxonomy.lazy import LazyTaxonList


class Glossary(GenericContent):

    zip_import_supported = True

    @property
    def zip_import_class(self):
        from .zip_import import GlossaryZipImporter
        return GlossaryZipImporter
    

    def taxa(self):
        taxonlist = LazyTaxonList()
        return taxonlist

    def higher_taxa(self):
        taxonlist = LazyTaxonList()
        return taxonlist

    def get_primary_localization(self):

        translation = {}

        translation[self.name] = self.name

        for entry in GlossaryEntry.objects.filter(glossary=self):
            translation[entry.term] = entry.term
            translation[entry.definition] = entry.definition
            
        return translation


    class Meta:
        verbose_name = _('Glossary')


FeatureModel = Glossary


class GlossaryEntry(models.Model):

    glossary = models.ForeignKey(Glossary, on_delete=models.CASCADE)

    term = models.CharField(max_length=355, unique=True)
    definition = models.TextField()

    @property
    def synonyms(self):
        return TermSynonym.objects.filter(glossary_entry=self)

    def __str__(self):
        return self.term

    class Meta:
        ordering = ['term']
    

class TermSynonym(models.Model):

    glossary_entry = models.ForeignKey(GlossaryEntry, on_delete=models.CASCADE)
    term = models.CharField(max_length=355, unique=True) # unique or unique_together ? current setup makes no sense

    def __str__(self):
        return self.term

    class Meta:
        unique_together = ('glossary_entry', 'term')
    

    

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

from app_kit.models import ContentImageMixin


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

    def get_primary_localization(self, meta_app=None):

        translation = super().get_primary_localization(meta_app)

        for entry in GlossaryEntry.objects.filter(glossary=self):
            translation[entry.term] = entry.term
            translation[entry.definition] = entry.definition

            for synonym in entry.synonyms:
                translation[synonym.term] = synonym.term
            
        return translation


    def get_primary_localization_terms_and_synonyms(self):

        all_entries = GlossaryEntry.objects.filter(glossary=self)
            
        terms_and_synonyms = []

        for entry in all_entries:

            terms_and_synonyms.append(entry.term)

            for synonym in entry.synonyms:
                terms_and_synonyms.append(synonym.term)

        return terms_and_synonyms


    class Meta:
        verbose_name = _('Glossary')


FeatureModel = Glossary


class GlossaryEntry(models.Model, ContentImageMixin):

    glossary = models.ForeignKey(Glossary, on_delete=models.CASCADE)

    term = models.CharField(max_length=355) # cannot be unique, a user might remove a linked glossary and add a new one
    definition = models.TextField()

    @property
    def synonyms(self):
        return TermSynonym.objects.filter(glossary_entry=self)

    def __str__(self):
        return self.term

    class Meta:
        ordering = ['term']
        unique_together = ('glossary', 'term')
    

class TermSynonym(models.Model):

    glossary_entry = models.ForeignKey(GlossaryEntry, on_delete=models.CASCADE)
    term = models.CharField(max_length=355) # unambiguous synonyms are detected during validation

    def __str__(self):
        return self.term

    class Meta:
        unique_together = ('glossary_entry', 'term')
    

    

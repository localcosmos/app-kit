'''
    BACKBONE TAXONOMY FEATURE
    this feature differs from the others:
    - only one backbone/AppTaxa list per app
'''
from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from app_kit.generic import GenericContent

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon

from taxonomy.lazy import LazyTaxon, LazyTaxonList
from taxonomy.models import TaxonomyModelRouter

CUSTOM_TAXONOMY_SOURCE = 'taxonomy.sources.custom'

class BackboneTaxonomy(GenericContent):

    ''' moved to JSON texts
    translations = TranslatedFields(
        name = models.CharField(max_length=255, null=True),
        slug = models.SlugField(unique=True, null=True),
    )
    '''

    # moved to options
    # include_full_tree = models.CharField(max_length=100, null=True, blank=True, choices=settings.TAXONOMY_DATABASES)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        '''
        # on creation, this would lead to an error
        if hasattr(self, "id") and self.id != None:
            self.taxon_sources = {}

            for feature in self.meta_app().features():
                feature_type = feature.feature.__class__.__name__ 
                if feature_type in self.accepted_sources:
                    self.taxon_sources[feature_type] = feature.content().values_list("content")
        '''

    # include full tree or not
    def include_full_tree(self):
        if self.global_options and 'include_full_tree' in self.global_options:
            return self.global_options['include_full_tree']
        return False


    def taxa(self):

        queryset = BackboneTaxa.objects.filter(backbonetaxonomy=self)
        taxonlist = LazyTaxonList(queryset)
        
        return taxonlist


    def higher_taxa(self):
        
        queryset = BackboneTaxa.objects.filter(backbonetaxonomy=self, taxon_include_descendants=True)
        taxonlist = LazyTaxonList(queryset)
        
        return taxonlist


    def descendant_taxa(self):
        # the nuids are stored directly, no lookup needed
        higher_taxa = BackboneTaxa.objects.filter(backbonetaxonomy=self, taxon_include_descendants=True,
                                                  taxon_nuid__isnull=False)

        lazy_taxonlist = LazyTaxonList()
        
        if higher_taxa:

            for higher_taxon in higher_taxa:

                models = TaxonomyModelRouter(higher_taxon.taxon_source)
                queryset = models.TaxonTreeModel.objects.filter(taxon_nuid__startswith=higher_taxon.taxon_nuid)

                lazy_taxonlist.add(queryset)

        return lazy_taxonlist


    def get_primary_localization(self, meta_app=None):

        # avoid circular import
        from app_kit.models import MetaAppGenericContent

        translation = super().get_primary_localization(meta_app)

        # add taxon locales for custom taxonomy
        custom_backbone_taxa = BackboneTaxa.objects.filter(backbonetaxonomy=self, taxon_source=CUSTOM_TAXONOMY_SOURCE)
        models = TaxonomyModelRouter(CUSTOM_TAXONOMY_SOURCE)

        for backbone_taxon in custom_backbone_taxa:

            taxontree_instance = backbone_taxon.taxon.tree_instance()

            if taxontree_instance:

                locale = models.TaxonLocaleModel.objects.filter(taxon=taxontree_instance,
                                                                language=self.primary_language).first()

                if locale:
                    translation[backbone_taxon.taxon_latname] = locale.name

                else:
                    translation[backbone_taxon.taxon_latname] = None

        # add all custom taxon locales to translation
        # a custom taxon might not be a BackboneTaxon, it can be added to a GenericForm etc
        all_custom_taxa_locales = models.TaxonLocaleModel.objects.all()

        for locale in all_custom_taxa_locales:
            taxon_latname = locale.taxon.taxon_latname
            if taxon_latname not in translation:
                translation[taxon_latname] = locale.name

        return translation


    class Meta:
        verbose_name = _('Backbone taxonomy')
        verbose_name_plural = _('Backbone taxonomies')


FeatureModel = BackboneTaxonomy


class BackboneTaxa(ModelWithRequiredTaxon):

    LazyTaxonClass = LazyTaxon

    backbonetaxonomy = models.ForeignKey(BackboneTaxonomy, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = _('Backbone Taxon')
        verbose_name_plural = _('Backbone Taxa')
        unique_together=('backbonetaxonomy', 'taxon_latname', 'taxon_author')
        ordering = ('taxon_latname', 'taxon_author')

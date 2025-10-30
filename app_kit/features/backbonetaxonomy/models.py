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
    
    zip_import_supported = True
    
    @property
    def zip_import_class(self):
        from .zip_import import BackbonetaxonomyZipImporter
        return BackbonetaxonomyZipImporter


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


        taxon_relationship_types = TaxonRelationshipType.objects.filter(backbonetaxonomy=self)
        for relationship_type in taxon_relationship_types:
            name = relationship_type.relationship_name
            if name and name not in translation:
                translation[name] = name
                
        taxon_relationships = TaxonRelationship.objects.filter(backbonetaxonomy=self)
        for relationship in taxon_relationships:
            description = relationship.description
            if description and description not in translation:
                translation[description] = description

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



class TaxonRelationshipType(models.Model):
    
    backbonetaxonomy = models.ForeignKey(BackboneTaxonomy, on_delete=models.CASCADE)
    
    # Abstract relationship name
    relationship_name = models.CharField(max_length=100)
    
    # Directional role names (optional)
    taxon_role = models.CharField(max_length=100, null=True, blank=True)
    related_taxon_role = models.CharField(max_length=100, null=True, blank=True)

    position = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.relationship_name

    class Meta:
        verbose_name = _('Taxon Relationship Type')
        verbose_name_plural = _('Taxon Relationship Types')
        unique_together = ('backbonetaxonomy', 'relationship_name')
        ordering = ('position', 'relationship_name')
    

class TaxonRelationship(ModelWithRequiredTaxon):
    
    LazyTaxonClass = LazyTaxon
    
    backbonetaxonomy = models.ForeignKey(BackboneTaxonomy, on_delete=models.CASCADE)
    
    related_taxon_source = models.CharField(max_length=100, choices=settings.TAXONOMY_DATABASES)
    related_taxon_name_uuid = models.UUIDField()
    related_taxon_latname = models.CharField(max_length=255)
    related_taxon_author = models.CharField(max_length=255, null=True, blank=True)
    related_taxon_nuid = models.CharField(max_length=255)
    related_taxon_include_descendants = models.BooleanField(default=False)
    
    relationship_type = models.ForeignKey(TaxonRelationshipType, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.relationship_type.relationship_name}: {self.taxon.taxon_latname} - {self.related_taxon_latname}"
    
    @property
    def related_taxon(self):
        models = TaxonomyModelRouter(self.related_taxon_source)
        taxon = models.TaxonTreeModel.objects.filter(name_uuid=self.related_taxon_name_uuid).first()
        if taxon:
            return LazyTaxon(instance=taxon)

        taxon_kwargs = {
            'taxon_source': self.related_taxon_source,
            'name_uuid': self.related_taxon_name_uuid,
            'taxon_latname': self.related_taxon_latname,
            'taxon_author': self.related_taxon_author,
            'taxon_nuid': self.related_taxon_nuid,
            'taxon_include_descendants': self.related_taxon_include_descendants,
        }
        return LazyTaxon(**taxon_kwargs)
    
    def set_related_taxon(self, lazy_taxon):
        self.related_taxon_source = lazy_taxon.taxon_source
        self.related_taxon_name_uuid = lazy_taxon.name_uuid
        self.related_taxon_latname = lazy_taxon.taxon_latname
        self.related_taxon_author = lazy_taxon.taxon_author
        self.related_taxon_nuid = lazy_taxon.taxon_nuid
        self.related_taxon_include_descendants = lazy_taxon.taxon_include_descendants

    class Meta:
        verbose_name = _('Taxon Relationship')
        verbose_name_plural = _('Taxon Relationships')
        ordering = ('taxon_latname', 'related_taxon_latname')

'''
    OBJECT CLASSES FEATURE
    - object classes are not taxa themselves
    - each object class has a primary taxon
    - additional taxa can be attached via a mapping table
'''
from django.db import models
from django.utils.translation import gettext_lazy as _

from app_kit.generic import GenericContent

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon

from taxonomy.lazy import LazyTaxonList


class ObjectClassManager(models.Manager):

    def create(self, object_classes, name, scientific_name, **extra_fields):


        instance = self.model(
            object_classes=object_classes,
            name=name,
            scientific_name=scientific_name,
            **extra_fields,
        )
        instance.save()
        return instance


class ObjectClasses(GenericContent):

    zip_import_supported = False

    def taxa(self):
        queryset = ObjectClassTaxon.objects.filter(object_class__object_classes=self)
        return LazyTaxonList(queryset)

    def higher_taxa(self):
        queryset = ObjectClassTaxon.objects.filter(
            object_class__object_classes=self,
            taxon_include_descendants=True,
        )
        return LazyTaxonList(queryset)

    class Meta:
        verbose_name = _('Object classes')
        verbose_name_plural = _('Object classes')


FeatureModel = ObjectClasses


class ObjectClass(models.Model):

    objects = ObjectClassManager()

    object_classes = models.ForeignKey(ObjectClasses, on_delete=models.CASCADE, related_name='entries')
    name = models.CharField(max_length=255)
    scientific_name = models.CharField(max_length=100) # language independent identifier for the object class
    description = models.TextField(null=True, blank=True)
    
    @property
    def taxa(self):
        queryset = ObjectClassTaxon.objects.filter(object_class=self)
        return queryset
    
    def is_taxon_compatible(self, taxon):
        valid_nuids = taxon.ancestor_nuids + [taxon.taxon_nuid]
                    
            
        is_compatible_taxon = self.taxa.filter(
            taxon_source=taxon.taxon_source,
            taxon_nuid__in=valid_nuids,
        ).exists()
        
        return is_compatible_taxon


    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Object class entry')
        verbose_name_plural = _('Object class entries')
        ordering = ['name']
        unique_together = ('object_classes', 'scientific_name')


class ObjectClassTaxon(ModelWithRequiredTaxon):

    object_class = models.ForeignKey('ObjectClass', on_delete=models.CASCADE, related_name='taxon_mappings')
    
    def __str__(self):
        return f"{self.object_class.name} - {self.taxon_latname}"

    class Meta:
        verbose_name = _('Object class taxon mapping')
        verbose_name_plural = _('Object class taxon mappings')
        ordering = ['taxon_latname']
        unique_together = ('object_class', 'name_uuid')
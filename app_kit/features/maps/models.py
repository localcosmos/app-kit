from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


from app_kit.generic import GenericContentManager, GenericContent
from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon

from taxonomy.lazy import LazyTaxonList

MAP_TYPES = (
    ('observations', _('Observations')),
)


class Map(GenericContent):

    map_type = models.CharField(max_length=255, choices=MAP_TYPES, default='observations')


    def get_primary_localization(self, meta_app=None):

        locale = super().get_primary_localization(meta_app)

        map_taxonomic_filters = MapTaxonomicFilter.objects.filter(map=self)

        for taxonomic_filter in map_taxonomic_filters:
            filter_name = taxonomic_filter.name
            locale[filter_name] = filter_name

        return locale


    def taxa(self):
        return LazyTaxonList()


    def higher_taxa(self):
        return LazyTaxonList()


    class Meta:
        verbose_name = _('Map')
        verbose_name_plural = _('Maps')

    
FeatureModel = Map


GEOMETRY_TYPES = (
    ('project_area', _('Project area')),
)

class MapGeometries(models.Model):

    map = models.ForeignKey(Map, on_delete=models.CASCADE)
    geometry_type = models.CharField(max_length=255, choices=GEOMETRY_TYPES)
    geometry = models.GeometryField(srid=3857)


class MapTaxonomicFilter(models.Model):

    map = models.ForeignKey(Map, on_delete=models.CASCADE)
    name = models.CharField(max_length=355)
    position = models.IntegerField(default=0)

    @property
    def taxa(self):
        return FilterTaxon.objects.filter(taxonomic_filter=self)

    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ('position',)


class FilterTaxon(ModelWithRequiredTaxon):

    taxonomic_filter = models.ForeignKey(MapTaxonomicFilter, on_delete=models.CASCADE)

    def __str__(self):
        if self.taxon.taxon_author:
            return '{0} {1}'.format(self.taxon.taxon_latname, self.taxon.taxon_author)
        else:
            return self.taxon_latname

    class Meta:
        unique_together = ('taxonomic_filter', 'name_uuid')
        verbose_name = _('Map Filter Taxon')



from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


from app_kit.generic import GenericContentManager, GenericContent

from taxonomy.lazy import LazyTaxonList

MAP_TYPES = (
    ('observations', _('Observations')),
)


class Map(GenericContent):

    map_type = models.CharField(max_length=255, choices=MAP_TYPES, default='observations')


    def get_primary_localization(self):

        locale = {}

        locale[self.name] = self.name

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

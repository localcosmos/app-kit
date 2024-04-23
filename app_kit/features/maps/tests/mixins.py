from app_kit.features.maps.models import Map, MapTaxonomicFilter

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

class WithMap:

    def create_map(self):
        app_map = Map.objects.create('Test Map', 'en')
        return app_map


class WithMapTaxonomicFilter:

    def create_taxonomic_filter(self):

        if not hasattr(self, 'map'):
            app_map = self.create_map()
        else:
            app_map = self.map
            
        map_taxonomic_filter = MapTaxonomicFilter(
            map=app_map,
            name='test filter'
        )
        map_taxonomic_filter.save()

        return map_taxonomic_filter


    def get_taxon(self):

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta')
        lazy_lacerta = LazyTaxon(instance=lacerta)

        return lazy_lacerta


    def get_taxon_post_data(self, taxon):
        post_data = {
            'taxon_0': taxon.taxon_source,
            'taxon_1': taxon.taxon_latname,
            'taxon_2': taxon.taxon_author,
            'taxon_3': taxon.name_uuid,
            'taxon_4': taxon.taxon_nuid,
        }

        return post_data
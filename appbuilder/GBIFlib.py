from app_kit.models import MetaCache

class GBIFlib:

    nubKey_cache_name = 'GBIF_nubKeys'

    def __init__(self):

        self.nubKey_cache = MetaCache.objects.filter(name=self.nubKey_cache_name).first()

        if not self.nubKey_cache:
            self.nubKey_cache = MetaCache(
                name=self.nubKey_cache_name,
                cache = {},
            )

            self.nubKey_cache.save()


    def get_nubKey(self, lazy_taxon):

        name_uuid = str(lazy_taxon.name_uuid)
        
        if name_uuid in self.nubKey_cache.cache:
            gbif_nubKey = self.nubKey_cache.cache[name_uuid]
        else:
            gbif_nubKey = lazy_taxon.gbif_nubKey()
            self.add_to_cache(name_uuid, gbif_nubKey)

        return gbif_nubKey


    def add_to_cache(self, name_uuid, nubKey):

        if not self.nubKey_cache.cache:
            self.nubKey_cache.cache = {}

        self.nubKey_cache.cache[name_uuid] = nubKey
        self.nubKey_cache.save()


    

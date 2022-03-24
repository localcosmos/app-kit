
class GBIFlib:

    nubKey_map = {}


    def get_nubKey(self, lazy_taxon):

        name_uuid = str(lazy_taxon.name_uuid)
        
        if name_uuid in self.nubKey_map:
            gbif_nubKey = self.nubKey_map[name_uuid]
        else:
            gbif_nubKey = lazy_taxon.gbif_nubKey()
            self.nubKey_map[name_uuid] = gbif_nubKey

        return gbif_nubKey

    

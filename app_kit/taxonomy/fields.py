from localcosmos_server.taxonomy.fields import HiddenTaxonField as BaseHiddenTaxonField
from taxonomy.lazy import LazyTaxon

class HiddenTaxonField(BaseHiddenTaxonField):
    
    lazy_taxon_class = LazyTaxon
from django.conf import settings
from django import template
register = template.Library()


from app_kit.features.taxon_profiles.models import TaxonProfile
from app_kit.features.nature_guides.models import NatureGuidesTaxonTree

@register.simple_tag
def get_taxon_profile(taxon):
    return TaxonProfile.objects.filter(taxon_source=taxon.taxon_source,
                                       taxon_latname=taxon.taxon_latname,
                                       taxon_author=taxon.taxon_author).first()

@register.simple_tag
def get_nature_guide_taxon(meta_node, nature_guide):
    taxon = NatureGuidesTaxonTree.objects.get(meta_node=meta_node, nature_guide=nature_guide)
    return taxon

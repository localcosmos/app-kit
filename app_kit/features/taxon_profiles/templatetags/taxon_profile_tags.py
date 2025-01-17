from django.conf import settings
from django import template
register = template.Library()


from app_kit.features.taxon_profiles.models import TaxonProfile, TaxonProfiles
from app_kit.features.nature_guides.models import NatureGuidesTaxonTree

@register.simple_tag
def get_taxon_profile(meta_app, taxon):
    taxon_profiles_link = meta_app.get_generic_content_links(TaxonProfiles).first()
    taxon_profiles = taxon_profiles_link.generic_content
    # col may have duplicates
    # since copying of bature guide branches (AWI), nature guide taxa may have duplicates if querying taxon_latname and taxon_author (taxon_source=app_kit.features.nature_guides)
    '''
    return TaxonProfile.objects.filter(taxon_source=taxon.taxon_source,
                                       taxon_latname=taxon.taxon_latname,
                                       taxon_author=taxon.taxon_author).first()
    '''
    return TaxonProfile.objects.filter(taxon_profiles=taxon_profiles, taxon_source=taxon.taxon_source,
                                       name_uuid=taxon.name_uuid).first()

@register.simple_tag
def get_nature_guide_taxon(meta_node, nature_guide):
    taxon = NatureGuidesTaxonTree.objects.get(meta_node=meta_node, nature_guide=nature_guide)
    return taxon
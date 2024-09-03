from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonProfilesNavigation,
                            TaxonProfilesNavigationEntry, TaxonProfilesNavigationEntryTaxa)

class WithTaxonProfilesNavigation:
    
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
        self.taxon_profiles = taxon_profiles_link.generic_content
        
        self.navigation = TaxonProfilesNavigation(
            taxon_profiles=self.taxon_profiles,
        )
        
        self.navigation.save()
        
    def create_navigation_entry(self, navigation=None, **kwargs):
        
        if not navigation:
            navigation = self.navigation
        
        taxon = kwargs.pop('taxon', None)
        
        navigation_entry = TaxonProfilesNavigationEntry(
            navigation=navigation,
            **kwargs
        )
        
        navigation_entry.save()
        
        if taxon:
            taxon_link = TaxonProfilesNavigationEntryTaxa(
                navigation_entry=navigation_entry,
            )
            
            taxon_link.set_taxon(taxon)
            taxon_link.save()
        
        return navigation_entry
    
    
    def taxon_to_post_data(self, taxon):
        post_data = {
            'taxon_0' : taxon.taxon_source,
            'taxon_1' : taxon.taxon_latname,
            'taxon_2' : taxon.taxon_author,
            'taxon_3' : str(taxon.name_uuid),
            'taxon_4' : taxon.taxon_nuid,
        }
        
        return post_data
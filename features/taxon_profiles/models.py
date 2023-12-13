from django.db import models

from django.utils.translation import gettext_lazy as _

from app_kit.models import ContentImageMixin
from app_kit.generic import GenericContent

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon
from taxonomy.lazy import LazyTaxonList, LazyTaxon

'''
    The content of the feature
    - there should be an multiiple choice options choosing text types
    - default is all text types
'''
from django.contrib.contenttypes.models import ContentType
from app_kit.models import MetaAppGenericContent

from taggit.managers import TaggableManager

class TaxonProfiles(GenericContent):

    zip_import_supported = True

    @property
    def zip_import_class(self):
        from .zip_import import TaxonProfilesZipImporter
        return TaxonProfilesZipImporter

    # moved to options
    # enable_wikipedia = models.BooleanField(default=True)
    # default_observation_form = models.IntegerField(null=True)

    # the taxa included in taxonprofiles do exist elsewhere in the app
    def taxa(self):
        return LazyTaxonList()

    def higher_taxa(self):
        return LazyTaxonList()

    def collected_taxa(self, published_only=True):

        # taxa that have explicit taxon profiles
        taxa_with_profile = TaxonProfile.objects.filter(taxon_profiles=self)
        existing_name_uuids = taxa_with_profile.values_list('name_uuid', flat=True)

        taxon_profiles_ctype = ContentType.objects.get_for_model(self)
        applink = MetaAppGenericContent.objects.get(content_type=taxon_profiles_ctype, object_id=self.pk)

        # avoid circular import the ugly way
        from app_kit.features.nature_guides.models import NatureGuide

        nature_guide_ctype = ContentType.objects.get_for_model(NatureGuide)

        nature_guide_links = MetaAppGenericContent.objects.filter(meta_app=applink.meta_app,
                                                                  content_type=nature_guide_ctype)

        taxonlist = LazyTaxonList()
        taxonlist.add(taxa_with_profile)

        for link in nature_guide_links:

            if published_only == True and link.publication_status != 'publish':
                continue
            nature_guide = link.generic_content
            nature_guide_taxa = nature_guide.taxa()
            nature_guide_taxa.exclude(name_uuid__in=existing_name_uuids)

            taxonlist.add_lazy_taxon_list(nature_guide_taxa)

        return taxonlist


    '''
    - we have to collect taxa first and then add their specific profiles
    '''
    def get_primary_localization(self, meta_app=None):
        locale = super().get_primary_localization(meta_app)

        taxon_query = TaxonProfile.objects.filter(taxon_profiles=self)
        taxa = LazyTaxonList(queryset=taxon_query)
        for lazy_taxon in taxa:

            taxon_query = {
                'taxon_source' : lazy_taxon.taxon_source,
                'taxon_latname' : lazy_taxon.taxon_latname,
                'taxon_author' : lazy_taxon.taxon_author,
            }

            taxon_profile = TaxonProfile.objects.filter(**taxon_query).first()

            if taxon_profile:

                for text in taxon_profile.texts():

                    # text_type_key = 'taxon_text_{0}'.format(text.taxon_text_type.id)
                    # short: use name as key (-> no duplicates in translation matrix)
                    text_type_key = text.taxon_text_type.text_type
                    locale[text_type_key] = text.taxon_text_type.text_type
                    
                    # text.text is a bad key, because if text.text changes, the translation is gone
                    # text.text are long texts, so use a different key which survives text changes
                    # locale[text.text] = text.text

                    short_text_key = self.get_short_text_key(text)

                    if text.text:
                        locale[short_text_key] = text.text

                    long_text_key = self.get_long_text_key(text)

                    if text.long_text:
                        locale[long_text_key] = text.long_text

                content_images_primary_localization = taxon_profile.get_content_images_primary_localization()
                locale.update(content_images_primary_localization)
        
        
        return locale


    def get_short_text_key(self, text):
        text_key = 'taxon_text_{0}_{1}'.format(text.taxon_text_type.id, text.id)
        return text_key

        
    def get_long_text_key(self, text):
        text_key = 'taxon_text_{0}_{1}_long'.format(text.taxon_text_type.id, text.id)
        return text_key


    class Meta:
        verbose_name = _('Taxon profiles')
        verbose_name_plural = _('Taxon profiles')


FeatureModel = TaxonProfiles


'''
    TaxonProfile
'''
from app_kit.generic import PUBLICATION_STATUS
class TaxonProfile(ContentImageMixin, ModelWithRequiredTaxon):

    LazyTaxonClass = LazyTaxon

    taxon_profiles = models.ForeignKey(TaxonProfiles, on_delete=models.CASCADE)

    publication_status = models.CharField(max_length=100, null=True, choices=PUBLICATION_STATUS)

    tags = TaggableManager()

    def texts(self):
        return TaxonText.objects.filter(taxon_profile=self).order_by('taxon_text_type__position')

    '''
    this checks taxon texts and vernacularnames[latter missing]
    '''
    def profile_complete(self):

        text_types = TaxonTextType.objects.filter(taxon_profiles=self.taxon_profiles)

        for text_type in text_types:

            taxon_text = TaxonText.objects.filter(taxon_profile=self, taxon_text_type=text_type).first()

            if not taxon_text or len(taxon_text.text) == 0:
                return False
            
        return True


    def __str__(self):
        return 'Taxon Profile of {0}'.format(self.taxon)
    

    class Meta:
        # unique_together=('taxon_source', 'taxon_latname', 'taxon_author')
        unique_together=('taxon_profiles', 'taxon_source', 'name_uuid')


class TaxonTextType(models.Model):

    taxon_profiles = models.ForeignKey(TaxonProfiles, on_delete=models.CASCADE)
    text_type = models.CharField(max_length=255) # the name of the text_type
    position = models.IntegerField(default=0)
    
    def __str__(self):
        return '{0}'.format(self.text_type)

    class Meta:
        unique_together = ('taxon_profiles', 'text_type')
        ordering = ['position']


class TaxonText(models.Model):
    taxon_profile = models.ForeignKey(TaxonProfile, on_delete=models.CASCADE)
    taxon_text_type = models.ForeignKey(TaxonTextType, on_delete=models.CASCADE)

    text = models.TextField(null=True)

    long_text = models.TextField(null=True)

    position = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('taxon_profile', 'taxon_text_type',)


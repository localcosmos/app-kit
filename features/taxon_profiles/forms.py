from django import forms

from django.utils.translation import gettext_lazy as _

from .models import TaxonTextType, TaxonText, TaxonProfile

from django.contrib.contenttypes.models import ContentType

from app_kit.forms import GenericContentOptionsForm
from localcosmos_server.forms import LocalizeableModelForm, LocalizeableForm


'''
    App-wide settings for taxonomic profiles
'''
from app_kit.features.generic_forms.forms import GenericFormChoicesMixin
class TaxonProfilesOptionsForm(GenericFormChoicesMixin, GenericContentOptionsForm):

    generic_form_choicefield = 'enable_observation_button'
    instance_fields = ['enable_observation_button']

    enable_wikipedia_button = forms.BooleanField(required=False)
    enable_gbif_occurrence_map_button = forms.BooleanField(required=False)
    enable_observation_button = forms.ChoiceField(required=False)



class ManageTaxonTextTypeForm(LocalizeableModelForm):

    localizeable_fields = ['text_type']

    class Meta:
        model = TaxonTextType
        fields = ('text_type', 'taxon_profiles')

        labels = {
            'text_type': _('Name of the text content, acts as heading'),
        }

        help_texts = {
            'text_type' : _('E.g. habitat. IMPORTANT: changing this affects all texts of this type.'),
        }

        widgets = {
            'taxon_profiles' : forms.HiddenInput,
        }


'''
    a form for managing all texts of one taxon at onces
'''
class ManageTaxonTextsForm(LocalizeableForm):

    localizeable_fields = []
    text_type_map = {}
    short_text_fields = []
    long_text_fields = []
    
    def __init__(self, taxon_profiles, taxon_profile=None, *args, **kwargs):
        self.localizeable_fields = []

        self.layoutable_simple_fields = []
        
        super().__init__(*args, **kwargs)

        
        types = TaxonTextType.objects.filter(taxon_profiles=taxon_profiles)

        for text_type in types:

            short_text_field_name = text_type.text_type
            long_text_field_name = self.get_long_text_form_field_name(text_type)

            self.text_type_map[short_text_field_name] = text_type
            self.text_type_map[long_text_field_name] = text_type

            self.short_text_fields.append(short_text_field_name)
            self.long_text_fields.append(long_text_field_name)

            short_text_field_label = _('%(text_type)s (short version)') % {'text_type': text_type.text_type}
            short_text_field = forms.CharField(widget=forms.Textarea(attrs={'placeholder': text_type.text_type}),
                                    required=False, label=short_text_field_label)
            short_text_field.taxon_text_type = text_type

            long_text_field_label = _('%(text_type)s (long version)') % {'text_type': text_type.text_type}
            long_text_field = forms.CharField(widget=forms.Textarea(attrs={'placeholder':text_type.text_type}),
                                    required=False, label=long_text_field_label)
            long_text_field.taxon_text_type = text_type

            if taxon_profile:
                content = TaxonText.objects.filter(taxon_text_type=text_type,
                                taxon_profile=taxon_profile).first()
                if content:
                    short_text_field.initial = content.text
                    long_text_field.initial = content.long_text
            
            self.fields[short_text_field_name] = short_text_field
            self.fields[long_text_field_name] = long_text_field

            self.localizeable_fields.append(short_text_field_name)
            self.localizeable_fields.append(long_text_field_name)

            self.fields[short_text_field_name].language = self.language
            self.fields[long_text_field_name].language = self.language
            
            self.layoutable_simple_fields.append(short_text_field_name)
            self.layoutable_simple_fields.append(long_text_field_name)
    
    
    def get_long_text_form_field_name(self, text_type):

        long_text_field_name = '{0}:longtext'.format(text_type.text_type)

        return long_text_field_name



''' currently unused
class SaveTaxonLocaleMixin:

    def save_taxon_locale(self, language, taxon_source, name_uuid, name):
        # save the vernacular name
        models = TaxonomyModelRouter(taxon_source)

        # check if the exact entry exists
        exists = models.TaxonLocaleModel.objects.filter(taxon_id=name_uuid, language=language,
            name=name).exists()
        
        if not exists:

            if taxon_source == CUSTOM_TAXONOMY_SOURCE:

                # check if the language exists
                language_exists = models.TaxonLocaleModel.objects.filter(taxon_id=name_uuid,
                                                                         language=language).exists()

                # this represents the primary entry for this language
                locale = None
                
                # if the language exists, overwrite the primary entry
                if language_exists:
                    # check if there is a preferred entry
                    locale = models.TaxonLocaleModel.objects.filter(taxon_id=name_uuid, language=language,
                                                                    preferred=True).first()

                if not locale:
                    locale = models.TaxonLocaleModel(
                        taxon_id=name_uuid,
                        language=language, preferred=True
                    )

                locale.name = name
                locale.save()
                

            # non-writeable source, use MetaTaxonomy
            else:

                locale = MetaVernacularNames.objects.filter(taxon_source=taxon_source, name_uuid=name_uuid,
                                                                language=language).first()
                
                if not locale:
                    locale = MetaVernacularNames(
                        taxon_source=lazy_taxon.taxon_source,
                        name_uuid=lazy_taxon.name_uuid,
                        taxon_latname=lazy_taxon.taxon_latname,
                        taxon_author=lazy_taxon.taxon_author,
                        taxon_nuid=lazy_taxon.taxon_nuid,
                        language=language,
                        preferred=True,
                    )
                

                if locale.name != name:
                    locale.name = name
                    locale.save()

        else:
            # if a meta entry exists, delete it
            meta = MetaVernacularNames.objects.filter(taxon_source=taxon_source, name_uuid=name_uuid,
                                                      language=language, preferred=True).first()

            if meta:
                meta.delete()

'''

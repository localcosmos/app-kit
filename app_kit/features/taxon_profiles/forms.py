from django.conf import settings
from django import forms

from django.utils.translation import gettext_lazy as _

from .models import (TaxonTextType, TaxonText, TaxonProfilesNavigationEntryTaxa, TaxonProfilesNavigationEntry)

from app_kit.validators import json_compatible

from app_kit.forms import GenericContentOptionsForm, GenericContentStatusForm
from localcosmos_server.forms import LocalizeableModelForm, LocalizeableForm
from localcosmos_server.taxonomy.fields import TaxonField
from taxonomy.lazy import LazyTaxon

from app_kit.utils import get_appkit_taxon_search_url


'''
    App-wide settings for taxonomic profiles
'''
from app_kit.features.generic_forms.forms import GenericFormChoicesMixin
class TaxonProfilesOptionsForm(GenericFormChoicesMixin, GenericContentOptionsForm):

    generic_form_choicefield = 'enable_observation_button'
    instance_fields = ['enable_observation_button']

    enable_wikipedia_button = forms.BooleanField(required=False, label=_('Enable Wikipedia button'))
    enable_gbif_occurrence_map_button = forms.BooleanField(required=False, label=_('Enable GBIF occurrence map button'))
    enable_observation_button = forms.ChoiceField(required=False, label=_('Enable observation button'))
    include_only_taxon_profiles_from_nature_guides = forms.BooleanField(required=False, label=_('Include only taxon profiles from Nature Guides'))
    
    enable_taxonomic_navigation = forms.BooleanField(required=False, label=_('Enable Taxonomic Navigation'))


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

        
        types = TaxonTextType.objects.filter(taxon_profiles=taxon_profiles).order_by('position')

        for text_type in types:

            short_text_field_name = text_type.text_type
            
            self.text_type_map[short_text_field_name] = text_type
            self.short_text_fields.append(short_text_field_name)
            
            short_text_field_label = text_type.text_type
            short_text_field = forms.CharField(widget=forms.Textarea(attrs={'placeholder': text_type.text_type}),
                                    required=False, label=short_text_field_label, validators=[json_compatible])
            short_text_field.taxon_text_type = text_type
            short_text_field.is_short_version = True

            self.fields[short_text_field_name] = short_text_field
            self.localizeable_fields.append(short_text_field_name)
            self.fields[short_text_field_name].language = self.language
            self.layoutable_simple_fields.append(short_text_field_name)
            

            if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
                long_text_field_name = self.get_long_text_form_field_name(text_type)
                self.text_type_map[long_text_field_name] = text_type
                self.long_text_fields.append(long_text_field_name)

                long_text_field_label = text_type.text_type
                long_text_field = forms.CharField(widget=forms.Textarea(attrs={'placeholder':text_type.text_type}),
                                        required=False, label=long_text_field_label, validators=[json_compatible])
                long_text_field.taxon_text_type = text_type
                long_text_field.is_short_version = False

                self.fields[long_text_field_name] = long_text_field
                self.localizeable_fields.append(long_text_field_name)
                self.fields[long_text_field_name].language = self.language
                self.layoutable_simple_fields.append(long_text_field_name)

            if taxon_profile:
                content = TaxonText.objects.filter(taxon_text_type=text_type,
                                taxon_profile=taxon_profile).first()
                if content:
                    short_text_field.initial = content.text

                    if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
                        long_text_field.initial = content.long_text
    
    
    def get_long_text_form_field_name(self, text_type):

        long_text_field_name = '{0}:longtext'.format(text_type.text_type)

        return long_text_field_name



class ManageTaxonProfilesNavigationEntryForm(LocalizeableForm):

    localizeable_fields = ['name', 'description']
    layoutable_simple_fields = ['description']

    
    name = forms.CharField(required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm
class AddTaxonProfilesNavigationEntryTaxonForm(AddSingleTaxonForm):
    
    lazy_taxon_class = LazyTaxon

    def __init__(self, *args, **kwargs):
        self.navigation_entry = kwargs.pop('navigation_entry', None)
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)
        
        self.fields['taxon'].label = _('Add taxon')
    
    def clean(self):
        cleaned_data = super().clean()
        taxon = cleaned_data.get('taxon', None)
        
        if taxon:
            
            already_exists_message = _('This taxon already exists in your navigation')
            
            tree_instance = taxon.tree_instance()
            
            if tree_instance and tree_instance.rank in ['species', 'infraspecies']:
                self.add_error('taxon', _('Adding of taxa below genus is not supported'))
                
            # at this point, custom taxa are not validated
            if not taxon.taxon_source == 'taxonomy.sources.custom':
            
                parent_taxa = []
                if self.parent:
                    parent_taxa = self.parent.taxa
                    
                    is_valid_descendant = False
                    
                    for parent_taxon in parent_taxa:
                        
                        if parent_taxon.taxon_latname == taxon.taxon_latname:
                            self.add_error('taxon', already_exists_message)
                            break
                        
                        if taxon.taxon_source == parent_taxon.taxon_source and taxon.taxon_nuid.startswith(parent_taxon.taxon_nuid):
                            is_valid_descendant = True
                            break
                        
                    if parent_taxa and not is_valid_descendant:
                        self.add_error('taxon', _('This taxon is not a valid descendant of the parent navigation entry'))
                        
                else:
                    
                    if self.navigation_entry:
                        children_taxa = TaxonProfilesNavigationEntryTaxa.objects.filter(navigation_entry__parent=self.navigation_entry)
                        
                        is_valid_parent = False
                        
                        if not children_taxa:
                            is_valid_parent = True
                            
                        for child_taxon in children_taxa:
                            if taxon.taxon_source == child_taxon.taxon_source and child_taxon.taxon_nuid.startswith(taxon.taxon_nuid):
                                is_valid_parent = True
                                break
                            
                        if not is_valid_parent:
                            self.add_error('taxon', _('This taxon is not a valid parent at this point in the navigation'))


            
            sibling_entries_query = TaxonProfilesNavigationEntry.objects.filter(parent=self.parent)
            taxa_query = TaxonProfilesNavigationEntryTaxa.objects.filter(
                taxon_latname=taxon.taxon_latname, navigation_entry_id__in=sibling_entries_query)
            
            if taxon.taxon_author:
                taxa_query = taxa_query.filter(taxon_author=taxon.taxon_author)
                
            if taxa_query.exists():
                self.add_error('taxon', already_exists_message)
                

        return cleaned_data
    

class TaxonProfileStatusForm(GenericContentStatusForm):
    
    is_featured = forms.BooleanField(required=False)

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

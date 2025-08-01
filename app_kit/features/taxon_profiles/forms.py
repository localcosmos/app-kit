from django.conf import settings
from django import forms

from django.utils.translation import gettext_lazy as _

from .models import (TaxonTextType, TaxonText, TaxonProfilesNavigationEntryTaxa, TaxonProfilesNavigationEntry,
                     TaxonTextTypeCategory)

from app_kit.validators import json_compatible

from app_kit.forms import GenericContentOptionsForm, GenericContentStatusForm
from localcosmos_server.forms import LocalizeableModelForm, LocalizeableForm
from taxonomy.lazy import LazyTaxon


'''
    App-wide settings for taxonomic profiles
'''
from app_kit.features.generic_forms.forms import GenericFormChoicesMixin
class TaxonProfilesOptionsForm(GenericFormChoicesMixin, GenericContentOptionsForm):

    generic_form_choicefield = 'enable_observation_button'
    instance_fields = ['enable_observation_button']

    #enable_wikipedia_button = forms.BooleanField(required=False, label=_('Enable Wikipedia button'))
    #enable_gbif_occurrence_map_button = forms.BooleanField(required=False, label=_('Enable GBIF occurrence map button'))
    enable_observation_button = forms.ChoiceField(required=False, label=_('Enable observation button'))
    include_only_taxon_profiles_from_nature_guides = forms.BooleanField(required=False, label=_('Include only taxon profiles from Nature Guides'))
    
    enable_taxonomic_navigation = forms.BooleanField(required=False, label=_('Enable Taxonomic Navigation'))
    
    version = forms.CharField(help_text=_('You can manually set you own version here. This will not affect the automated versioning.'), required=False)


class ManageTaxonTextTypeForm(LocalizeableModelForm):

    localizeable_fields = ['text_type']

    class Meta:
        model = TaxonTextType
        fields = ('text_type', 'taxon_profiles', 'category')

        labels = {
            'text_type': _('Name of the text content, acts as heading'),
        }

        help_texts = {
            'text_type' : _('E.g. habitat. IMPORTANT: changing this affects all texts of this type.'),
        }

        widgets = {
            'taxon_profiles' : forms.HiddenInput,
        }



class ManageTaxonTextTypeCategoryForm(LocalizeableModelForm):

    localizeable_fields = ['name']

    class Meta:
        model = TaxonTextTypeCategory
        fields = ('name', 'taxon_profiles')

        labels = {
            'name': _('Name of the category'),
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
    
    short_profile = forms.CharField(widget=forms.Textarea, required=False, validators=[json_compatible])
    
    def __init__(self, taxon_profiles, taxon_profile=None, *args, **kwargs):
        self.localizeable_fields = ['short_profile']

        self.layoutable_simple_fields = []
        
        self.has_categories = False
        
        super().__init__(*args, **kwargs)
        
        categories = [None] + list(TaxonTextTypeCategory.objects.filter(taxon_profiles=taxon_profiles))
        
        if len(categories) > 1:
            self.has_categories = True
        
        for category_index, category in enumerate(categories, 1):
            
            types = TaxonTextType.objects.filter(taxon_profiles=taxon_profiles, category=category).order_by('category', 'position')
            
            category_label = 'uncategorized'
            if category:
                category_label = category.name
                
            category_helper_field = forms.CharField(widget=forms.HiddenInput(), label=category_label, required=False)
            category_helper_field.category = category
            category_helper_field.is_category_field = True
            category_helper_field.text_type_count = types.count()
            category_helper_field.is_first_category = False
            category_helper_field.is_last = False
            
            if category_index == 2:
                category_helper_field.is_first_category = True
                
            if not types:
                category_helper_field.is_last = True
            
            self.fields[category_label] = category_helper_field
            
            for field_index, text_type in enumerate(types, 1):

                short_text_field_name = text_type.text_type
                
                self.text_type_map[short_text_field_name] = text_type
                self.short_text_fields.append(short_text_field_name)
                
                short_text_field_label = text_type.text_type
                short_text_field = forms.CharField(widget=forms.Textarea(attrs={'placeholder': text_type.text_type}),
                                        required=False, label=short_text_field_label, validators=[json_compatible])
                short_text_field.taxon_text_type = text_type
                short_text_field.is_short_version = True
                short_text_field.is_last = False
                short_text_field.taxon_text = None

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
                    long_text_field.is_last = False

                    self.fields[long_text_field_name] = long_text_field
                    self.localizeable_fields.append(long_text_field_name)
                    self.fields[long_text_field_name].language = self.language
                    self.layoutable_simple_fields.append(long_text_field_name)
                    
                if field_index == len(types):
                    if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
                        long_text_field.is_last = True
                    else:
                        short_text_field.is_last = True

                if taxon_profile:
                    content = TaxonText.objects.filter(taxon_text_type=text_type,
                                    taxon_profile=taxon_profile).first()
                    if content:
                        short_text_field.initial = content.text
                        short_text_field.taxon_text = content

                        if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
                            long_text_field.initial = content.long_text
                            long_text_field.taxon_text = content
    
    
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

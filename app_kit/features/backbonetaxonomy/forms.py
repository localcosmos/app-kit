from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.fields import BLANK_CHOICE_DASH


from taxonomy.lazy import LazyTaxon

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa

from localcosmos_server.taxonomy.fields import TaxonField

from django.urls import reverse

from taxonomy.models import TaxonomyModelRouter
CUSTOM_TAXONOMY_SOURCE = 'taxonomy.sources.custom'

# this should be a simpletaxonautocompletewidget searching all backbone taxa
from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from localcosmos_server.forms import LocalizeableModelForm

from .models import TaxonRelationshipType

class SearchTaxonomicBackboneForm(AddSingleTaxonForm):
    
    lazy_taxon_class = LazyTaxon

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['taxon'].label = _('Search app taxa')


class AddMultipleTaxaForm(forms.Form):
    source = forms.ChoiceField(choices=settings.TAXONOMY_DATABASES)
    taxa = forms.CharField(widget=forms.Textarea,
                           label = _('Enter your taxa below. Only scientific names, separated by commas:'))


fulltree_choices = BLANK_CHOICE_DASH + list(settings.TAXONOMY_DATABASES)


class ManageFulltreeForm(forms.ModelForm):

    include_full_tree = forms.ChoiceField(choices=fulltree_choices, required=False,
                                          label=_('Select taxonomic systems'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = kwargs.get('instance', None)
        
        if instance and instance.global_options and 'include_full_tree' in instance.global_options:
            self.fields['include_full_tree'].initial = instance.global_options['include_full_tree']
    
    class Meta:
        model = BackboneTaxonomy
        fields = []


class SwapTaxonForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        
        taxon_search_url = reverse('search_taxon')

        super().__init__(*args, **kwargs)

        # the field_kwargs are also passed to the widget
        field_kwargs = {
            'taxon_search_url' : taxon_search_url,
            'descendants_choice' : False,
            'fixed_taxon_source' : False,
            'widget_attrs' : {},
            'lazy_taxon_class': LazyTaxon,
        }

        self.fields['from_taxon'] = TaxonField(label=_('Taxon 1 (will be replaced by Taxon 2)'), required=True, **field_kwargs)
        self.fields['to_taxon'] = TaxonField(label=_('Taxon 2 (will repace Taxon 1)'), required=True, **field_kwargs)
        
        
    # you ma y not select the same taxon twice
    def clean(self):
        cleaned_data = super().clean()
        from_taxon = cleaned_data.get('from_taxon')
        to_taxon = cleaned_data.get('to_taxon')

        if from_taxon and to_taxon and from_taxon == to_taxon:
            raise forms.ValidationError(_('You cannot select the same taxon twice.'))
        
        return cleaned_data
    
    
class TaxonRelationshipTypeForm(LocalizeableModelForm):

    localizeable_fields = ['relationship_name', 'taxon_role', 'related_taxon_role']
    
    
    def clean(self):
        cleaned_data = super().clean()
        taxon_role = cleaned_data.get('taxon_role')
        related_taxon_role = cleaned_data.get('related_taxon_role')

        if taxon_role and not related_taxon_role:
            raise forms.ValidationError(_('If a role for the main taxon is provided, a role for the related taxon must also be provided.'))

        if related_taxon_role and not taxon_role:
            raise forms.ValidationError(_('If a role for the related taxon is provided, a role for the main taxon must also be provided.'))

        return cleaned_data

    class Meta:
        model = TaxonRelationshipType
        fields = ['relationship_name', 'taxon_role', 'related_taxon_role']
        help_texts = {
            'relationship_name': _('Abstract name like "predation", "competition", etc.'),
            'taxon_role': _('Role of the main taxon (e.g., "predator", "host", "parasite")'),
            'related_taxon_role': _('Role of the related taxon (e.g., "prey", "guest", "host")'),
        }


class TaxonRelationshipForm(forms.Form):
    
    description = forms.CharField(widget=forms.Textarea, required=False,
                                  label=_('Description'),
                                  help_text=_('Optional description of this relationship.'))

    
    def __init__(self, relationship_type, *args, **kwargs):
        
        taxon_search_url = reverse('search_taxon')
        
        super().__init__(*args, **kwargs)
        
        
        field_kwargs = {
            'taxon_search_url' : taxon_search_url,
            'descendants_choice' : False,
            'fixed_taxon_source' : False,
            'widget_attrs' : {},
            'lazy_taxon_class': LazyTaxon,
        }

        self.fields['taxon'] = TaxonField(label=_('Main taxon'), required=True, **field_kwargs)
        self.fields['related_taxon'] = TaxonField(label=_('Related taxon'), required=True, **field_kwargs)

        self.relationship_type = relationship_type
        if relationship_type.taxon_role:
            self.fields['taxon'].label = relationship_type.taxon_role
        if relationship_type.related_taxon_role:
            self.fields['related_taxon'].label = relationship_type.related_taxon_role
            
        self.order_fields(['taxon', 'related_taxon', 'description'])
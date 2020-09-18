from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa

from localcosmos_server.taxonomy.fields import TaxonField

from django.urls import reverse

from taxonomy.models import TaxonomyModelRouter
CUSTOM_TAXONOMY_SOURCE = 'taxonomy.sources.custom'

# this should be a simpletaxonautocompletewidget searching all backbone taxa
from localcosmos_server.taxonomy.forms import AddSingleTaxonForm
class SearchTaxonomicBackboneForm(AddSingleTaxonForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['taxon'].label = _('Search app taxa')


class AddMultipleTaxaForm(forms.Form):
    source = forms.ChoiceField(choices=settings.TAXONOMY_DATABASES)
    taxa = forms.CharField(widget=forms.Textarea,
                           label = _('Enter your taxa below. Only scientific names, separated by commas:'))


from django.db.models.fields import BLANK_CHOICE_DASH
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



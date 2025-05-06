from django import forms
from django.utils.translation import gettext_lazy as _

from localcosmos_server.forms import LocalizeableForm

from taxonomy.models import TaxonomyModelRouter
custom_taxonomy_models = TaxonomyModelRouter('taxonomy.sources.custom')

from localcosmos_server.taxonomy.fields import TaxonField
from app_kit.utils import get_appkit_taxon_search_url

TAXON_RANK_CHOICES = (
    ('', '-----'),
    ('kingdom', _('Kingdom')),
    ('phylum', _('Phylum')),
    ('class', _('Class')),
    ('order', _('Order')),
    ('family', _('Family')),
    ('genus', _('Genus')),
    ('species', _('Species')),
    ('subspecies', _('Subspecies')),
)

class ManageCustomTaxonForm(LocalizeableForm):

    parent_name_uuid = forms.UUIDField(widget=forms.HiddenInput, required=False)
    name_uuid = forms.UUIDField(widget=forms.HiddenInput, required=False)
    taxon_latname = forms.CharField(label=_('Language-independent name'), help_text=_('e.g. the Latin name'))
    taxon_author = forms.CharField(label=_('Author'), required=False)
    name = forms.CharField(help_text=_('Vernacular name'))
    rank = forms.ChoiceField(required=False, choices=TAXON_RANK_CHOICES)

    localizeable_fields = ['name']

    def clean(self):
        latname = self.cleaned_data.get('latname', None)
        author = self.cleaned_data.get('author', None)
        name_uuid = self.cleaned_data.get('name_uuid', None)

        if latname and name_uuid is None:
                        
            exists = custom_taxonomy_models.TaxonTreeModel.objects.filter(taxon_latname__iexact=latname.upper(), taxon_author__iexact=author.upper()).exists()

            if exists:
                raise forms.ValidationError(_('A taxon with this language-independent name already exists.'))
        return self.cleaned_data


class MoveCustomTaxonForm(forms.Form):
    
    def __init__(self, taxon, *args, **kwargs):
        self.taxon = taxon
        super().__init__(*args, **kwargs)

    new_parent_taxon = TaxonField(label=_('Move to'), help_text=_('Enter latin or vernacular name, then select.'),
                                  taxon_search_url=get_appkit_taxon_search_url, fixed_taxon_source='taxonomy.sources.custom')

    def clean(self):

        new_parent_taxon = self.cleaned_data.get('new_parent_taxon', None)

        if new_parent_taxon is not None:

            if new_parent_taxon.taxon_nuid.startswith(self.taxon.taxon_nuid):
                raise forms.ValidationError(_('Cannot move a taxon into its own descendants. Please select another taxon.'))

        return self.cleaned_data

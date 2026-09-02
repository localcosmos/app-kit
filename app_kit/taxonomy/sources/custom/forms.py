from django import forms
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from localcosmos_server.forms import LocalizeableForm

from taxonomy.models import TaxonomyModelRouter
custom_taxonomy_models = TaxonomyModelRouter('taxonomy.sources.custom')

from localcosmos_server.taxonomy.fields import TaxonField
from app_kit.utils import get_appkit_taxon_search_url

TAXON_RANK_CHOICES = (
    ('', '-----'),
    ('kingdom', _('Kingdom')),
    ('phylum', _('Phylum')),
    ('subphylum', _('Subphylum')),
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
    taxon_latname = forms.CharField(label=_('Scientific name'), help_text=_('e.g. the Latin name'))
    taxon_author = forms.CharField(label=_('Author'), required=False)
    name = forms.CharField(help_text=_('Vernacular name'))
    rank = forms.ChoiceField(required=False, choices=TAXON_RANK_CHOICES)

    localizeable_fields = ['name']
    
    def __init__(self, *args, **kwargs):
        
        self.localizeable_fields = ['name']
        
        super().__init__(*args, **kwargs)
                
        name_uuid = self.initial.get('name_uuid', None)
        input_language = self.initial.get('input_language', None)
        
        
        if name_uuid is not None and input_language is not None:
           existing_locales = custom_taxonomy_models.TaxonLocaleModel.objects.filter(taxon__name_uuid=name_uuid).exclude(language=input_language)

           locale_field_names = []
           for locale in existing_locales:
               field_label = _('Name') + f' ({locale.language})'
               help_text = _('Vernacular name in this language')
               field = forms.CharField(label=field_label, help_text=help_text, required=False, initial=locale.name)
               field_name = f'name_{locale.language}_{locale.id}'
               self.localizeable_fields.append(field_name)
               field.language = locale.language
               self.fields[field_name] = field
               locale_field_names.append(field_name)

           if locale_field_names:
               name_index = list(self.fields).index('name')
               field_order = [k for k in self.fields if k not in locale_field_names]
               for lf in reversed(locale_field_names):
                   field_order.insert(name_index + 1, lf)
               self.order_fields(field_order)
                       

    def clean(self):
        latname = self.cleaned_data.get('latname', None)
        author = self.cleaned_data.get('author', None)
        name_uuid = self.cleaned_data.get('name_uuid', None)

        if latname and name_uuid is None:
                        
            exists = custom_taxonomy_models.TaxonTreeModel.objects.filter(taxon_latname__iexact=latname.upper(), taxon_author__iexact=author.upper()).exists()

            if exists:
                raise forms.ValidationError(_('A taxon with this language-independent name already exists.'))
        return self.cleaned_data
    

LANGUAGE_CHOICES = [('', _('Select language'))] + sorted(settings.LANGUAGES, key=lambda x: x[1])

class AddCustomTaxonLocaleForm(forms.Form):

    name_uuid = forms.UUIDField(widget=forms.HiddenInput, required=True)
    language = forms.ChoiceField(choices=LANGUAGE_CHOICES)
    name = forms.CharField(label=_('Vernacular name'), help_text=_('Vernacular name'))


class MoveCustomTaxonForm(forms.Form):
    
    def __init__(self, taxon, *args, **kwargs):
        self.taxon = taxon
        super().__init__(*args, **kwargs)

    new_parent_taxon = TaxonField(label=_('Move to'), help_text=_('Enter latin or vernacular name, then select.'),
                                  taxon_search_url=get_appkit_taxon_search_url, fixed_taxon_source='taxonomy.sources.custom', required=False)
    
    move_to_root = forms.BooleanField(label=_('Move to root'), required=False, help_text=_('Check this box to move the taxon to the root of the taxonomy.'))

    def clean(self):

        new_parent_taxon = self.cleaned_data.get('new_parent_taxon', None)
        move_to_root = self.cleaned_data.get('move_to_root', False)

        if new_parent_taxon is not None:

            if new_parent_taxon.taxon_nuid.startswith(self.taxon.taxon_nuid):
                raise forms.ValidationError(_('Cannot move a taxon into its own descendants. Please select another taxon.'))
        
        if move_to_root and new_parent_taxon is not None:
            raise forms.ValidationError(_('Cannot select both a new parent taxon and move to root. Please select one option.'))

        return self.cleaned_data

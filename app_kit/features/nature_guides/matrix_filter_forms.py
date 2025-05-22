# forms for matrix filters
from django.utils.translation import gettext_lazy as _

from django import forms

from localcosmos_server.forms import LocalizeableForm

from .models import MatrixFilter
from .matrix_filters import MATRIX_FILTER_TYPES

from .forms import is_active_field


IDENTIFICATION_MEANS = (
    #('', '--------'),
    ('visual', _('visual')),
    ('tactile', _('tactile')),
    ('auditory', _('auditory')),
    ('microscope', _('microscope')),
    ('scalpel', _('scalpel')),
    ('gustatory', _('gustatory')),
    ('olfactory', _('olfactory')),
)

class MatrixFilterManagementForm(LocalizeableForm):
    
    name = forms.CharField(label=_('Name of filter or trait'),
                           help_text=_("What is described by the filter, e.g. 'length of nose'"))
    filter_type = forms.ChoiceField(choices=MATRIX_FILTER_TYPES, widget=forms.HiddenInput)

    identification_means = forms.MultipleChoiceField(choices=IDENTIFICATION_MEANS, required=False,
                        label=_('Means of identification'), widget=forms.CheckboxSelectMultiple)

    weight = forms.IntegerField(min_value=0, max_value=10, initial=1,
                                help_text=_('0-10. Use a high value if the trait is easily recoginzed, and a low one if it is more difficult.'))

    is_active = is_active_field

    localizeable_fields = ['name'] #, 'description']


    def __init__(self, meta_node, matrix_filter, *args, **kwargs):
        self.matrix_filter = matrix_filter
        self.meta_node = meta_node
        super().__init__(*args, **kwargs)

        if self.matrix_filter:
            self.fields['name'].help_text = self.matrix_filter.matrix_filter_type.help_text
        

    def clean_name(self):
        name = self.cleaned_data.get('name', None)

        if name:

            if not self.matrix_filter:
                exists = MatrixFilter.objects.filter(meta_node=self.meta_node, name=name).exists()
            else:
                exists = MatrixFilter.objects.filter(meta_node=self.meta_node, name=name).exclude(pk=self.matrix_filter.pk)

            if exists:
                del self.cleaned_data['name']
                raise forms.ValidationError(_('A matrix filter with this name already exists.'))

        return name


class MatrixFilterManagementFormWithUnit(MatrixFilterManagementForm):
    unit = forms.CharField(label=_('Unit (abbreviated)'), max_length=10, required=False,
                           help_text=_('Short text for unit, like m or cm, independent of language.'))
    unit_verbose = forms.CharField(max_length=100, required=False, label = _('Name of unit'),
                                   help_text=_('Full name of the unit, like meters or centimeters.'))

    field_order = ['input_language', 'name', 'filter_type', 'unit', 'unit_verbose']



class MatrixFilterManagementFormWithMultipleValues(MatrixFilterManagementForm):
    
    allow_multiple_values = forms.BooleanField(label=_('allow the selection of multiple values (AND logic)'),
                                help_text=_('The end user will be able to select more than one value. The selected values will be treated as "OR".'),
                                required=False)



class MatrixFilterManagementFormWithTolerance(MatrixFilterManagementFormWithUnit):
    tolerance = forms.IntegerField(required=False, label=_('Tolerance (percentage)'), help_text='eg if set to 10, the user input is still valid if it is off by 10% of your configured range')

    field_order = ['input_language', 'name', 'filter_type', 'unit', 'unit_verbose', 'tolerance']

'''
class MatrixFilterManagementFormWithMultipleValuesAndUnit(MatrixFilterManagementFormWithUnit):
    allow_multiple_values = forms.BooleanField(label=_('allow the user to select multiple values'), required=False)
'''

class DescriptiveTextAndImagesFilterManagementForm(MatrixFilterManagementFormWithMultipleValues):
    pass

class TextOnlyFilterManagementForm(MatrixFilterManagementFormWithMultipleValues):
    pass

class RangeFilterManagementForm(MatrixFilterManagementFormWithTolerance):

    localizeable_fields = ['name', 'unit_verbose']

    min_value = forms.FloatField(label=_('Min'))
    max_value = forms.FloatField(label=_('Max'))   
    step = forms.FloatField(help_text=_('Range will be rendered as a slider. Step defines the step of this slider.'))

    field_order = ['input_language', 'name', 'filter_type', 'min_value', 'max_value', 'step', 'unit',
                   'unit_verbose', 'tolerance']
    
    
    def clean_max_value(self):
        min_value = self.cleaned_data.get('min_value', None)
        max_value = self.cleaned_data.get('max_value', None)

        if min_value and max_value and min_value > max_value:
            #del self.cleaned_data['min_value']
            #del self.cleaned_data['max_value']
            raise forms.ValidationError(_('Max needs to be higher than min.'))
        
        return max_value


class ColorFilterManagementForm(MatrixFilterManagementFormWithMultipleValues):
    pass


class NumberFilterManagementForm(MatrixFilterManagementFormWithUnit):

    localizeable_fields = ['name', 'unit_verbose']
    
    numbers = forms.CharField(label=_('Selectable Numbers'), help_text=_('Comma-separated list, e.g. 1,2,3.1,5'))

    field_order = ['input_language', 'name', 'filter_type', 'numbers', 'unit', 'unit_verbose']
    
    def clean_numbers(self):
        numbers = self.cleaned_data.get('numbers', None)

        number_list = []

        numbers = numbers.strip(',')

        if numbers:
            str_list = numbers.split(',')
            for counter, i in enumerate(str_list):                
                try:
                    number_list.append(float(i))
                except:
                    del self.cleaned_data['numbers']
                    raise forms.ValidationError(
                        _('Only comma separated numbers are allowed. Incorrect character: %s' %(str_list[counter]))
                        )

        number_list.sort()
        return number_list


'''
    Taxonomic Filtering
    - the latname should be good enough
    - use the same latname across all sources
'''
from localcosmos_server.taxonomy.fields import TaxonField
from app_kit.utils import get_appkit_taxon_search_url
from .matrix_filters import PREDEFINED_TAXONOMIC_FILTERS
class TaxonFilterManagementForm(MatrixFilterManagementForm):

    localizeable_fields = ['name']
    
    taxonomic_filters = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)
    add_custom_taxonomic_filter = TaxonField(required=False, taxon_search_url=get_appkit_taxon_search_url)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        predefined_latnames = [p[0] for p in PREDEFINED_TAXONOMIC_FILTERS]

        custom_choices = []

        if self.matrix_filter and self.matrix_filter.encoded_space:
            for taxonfilter in self.matrix_filter.encoded_space:
                if taxonfilter['latname'] not in predefined_latnames:
                    choice = (taxonfilter['latname'], taxonfilter['latname'])
                    custom_choices.append(choice)
        
        self.fields['taxonomic_filters'].choices = list(PREDEFINED_TAXONOMIC_FILTERS) + custom_choices

from django import forms
from django.forms.widgets import Widget, MultiWidget, SelectMultiple, RadioSelect

from django.template import loader, Context


'''
    some choices need to consist of more than 2 indices [value, label, {}]
'''
class ChoiceExtraKwargsMixin:

    def clean_choices(self):
        
        # choices can be any iterable, but we may need to render this widget
        # multiple times. Thus, collapse it into a list so it can be consumed
        # more than once.
        self.choices_extra_kwargs = {}

        cleaned_choices = []

        for index, full_choice in enumerate(list(self.choices)):

            choice = (full_choice[0], full_choice[1])

            if len(full_choice) > 2:
                self.choices_extra_kwargs[index] = full_choice[2]

            cleaned_choices.append(choice)
        
        self.choices = cleaned_choices


    def optgroups(self, name, value, attrs):
        self.clean_choices()
        return super().optgroups(name, value, attrs)

    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=None, attrs=None)

        if index in self.choices_extra_kwargs:
            option.update(self.choices_extra_kwargs[index])
        return option


'''
    Although the e.g. DecimalField min_value and max_value are set, for rendering a slider,
    the widget needs those values as well -> supply the MatrixFilter instance for the widget
'''
class MatrixFilterMixin:

    def __init__(self, matrix_filter, *args, **kwargs):
        self.matrix_filter = matrix_filter
        self.extra_context = kwargs.pop('extra_context', {})
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):

        context = super().get_context(name, value, attrs)

        if not hasattr(self, 'matrix_filter'):
            raise ValueError('MatrixFilterMixin neeeds the matrix_filter attribute')
        
        context['matrix_filter'] = self.matrix_filter

        context.update(self.extra_context)

        return context
    


'''
    Widgets for Traits
    - = the matrix key
'''

'''
    RangeTraitWidget
    - displays as a slider or a range slider
'''
class RangePropertyWidget(MatrixFilterMixin, Widget):

    template_name = 'nature_guides/widgets/range.html'

    def get_context(self, name, value, attrs):

        context = super().get_context(name, value, attrs)

        if 'value' not in context['widget']:
            context['widget']['value'] = None
        
        return context


''' NODE DEFINITION
    - Widgets for adding new Nodes to a matrixkey
'''
class DefineRangeSpaceWidget(MultiWidget):

    template_name = 'nature_guides/widgets/define_range_widget.html'

    def __init__(self, attrs={}):

        self.extra_context = attrs.pop('extra_context', {})
        
        widgets = (
            forms.NumberInput(attrs=attrs),
            forms.NumberInput(attrs=attrs),
        )
        super().__init__(widgets, attrs)


    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context.update(self.extra_context)

        return context


    def decompress(self, value):

        data_list = []

        if value:
            
            data_list = [float(i) for i in value]
        
        return data_list


'''
    these depend on the previously defined selectable values
'''
class DefineDescriptionWidget(MatrixFilterMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/define_description_widget.html' 
    

class DefineColorsWidget(MatrixFilterMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/define_colors_widget.html'

    
''' END-USER INPUT
    Widgets for the end-user matrix key
    - Select and SelectMultiple with templates
'''
class SliderSelectMultipleColors(ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_colors.html'

class SliderRadioSelectColor(ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_colors.html'


class SliderSelectMultipleDescriptors(ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_patterns.html'

class SliderRadioSelectDescriptor(ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_patterns.html'


class SliderSelectMultipleNumbers(SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_numbers.html'

class SliderRadioSelectNumber(RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_numbers.html'


class SliderSelectMultipleTaxonfilters(ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_taxonfilters.html'

class SliderRadioSelectTaxonfilter(ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_taxonfilters.html'

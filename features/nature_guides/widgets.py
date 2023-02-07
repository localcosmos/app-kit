from django import forms
from django.forms.widgets import Widget, MultiWidget, SelectMultiple, RadioSelect, CheckboxSelectMultiple
from django.contrib.contenttypes.models import ContentType

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


class WidgetExtraContextMixin:

    def __init__(self, *args, **kwargs):
        self.extra_context = kwargs.pop('extra_context', {})
        super().__init__(*args, **kwargs)


    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context.update(self.extra_context)
        return context
        
'''
    Although the e.g. DecimalField min_value and max_value are set, for rendering a slider,
    the widget needs those values as well -> supply the MatrixFilter instance for the widget
'''
class MatrixFilterMixin(WidgetExtraContextMixin):

    def __init__(self, matrix_filter, *args, **kwargs):
        self.matrix_filter = matrix_filter
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):

        context = super().get_context(name, value, attrs)

        if not hasattr(self, 'matrix_filter'):
            raise ValueError('MatrixFilterMixin needs the matrix_filter attribute')
        
        context['matrix_filter'] = self.matrix_filter
        return context
    

class MatrixFilterMetaAppMixin(MatrixFilterMixin):

    def __init__(self, meta_app, *args, **kwargs):
        self.meta_app = meta_app
        super().__init__(*args, **kwargs)


    def get_context(self, name, value, attrs):

        context = super().get_context(name, value, attrs)
        context['meta_app'] = self.meta_app

        return context


'''
    Widgets for Traits
    - = the matrix key
'''

'''
    RangeTraitWidget
    - displays as a slider or a range slider
'''
class RangePropertyWidget(MatrixFilterMetaAppMixin, Widget):

    template_name = 'nature_guides/widgets/range.html'

    def get_context(self, name, value, attrs):

        context = super().get_context(name, value, attrs)

        if 'value' not in context['widget']:
            context['widget']['value'] = None
        
        return context


''' NODE DEFINITION
    - Widgets for adding new Nodes to a matrixkey
'''
class DefineRangeSpaceWidget(WidgetExtraContextMixin, MultiWidget):

    template_name = 'nature_guides/widgets/define_range_widget.html'

    def __init__(self, attrs={}, **kwargs):

        widgets = (
            forms.NumberInput(attrs=attrs),
            forms.NumberInput(attrs=attrs),
        )
        super().__init__(widgets, attrs)


    def decompress(self, value):

        data_list = []

        if value:
            
            data_list = [float(i) for i in value]
        
        return data_list


'''
    Widgets for assigning values to a node (child)
    these depend on the previously defined selectable values
'''
class DefineDescriptionWidget(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/define_description_widget.html'


class DefineTextDescriptionWidget(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/define_text_description_widget.html' 
    

class DefineColorsWidget(MatrixFilterMetaAppMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/define_colors_widget.html'
    

class DefineNumbersWidget(WidgetExtraContextMixin, CheckboxSelectMultiple):
    template_name = 'nature_guides/widgets/define_numbers_widget.html'

    
''' END-USER INPUT
    Widgets for the end-user matrix key
    - Select and SelectMultiple with templates
'''
class SliderSelectMultipleColors(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_colors.html'

class SliderRadioSelectColor(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_colors.html'


class SliderSelectMultipleDescriptors(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_patterns.html'

class SliderRadioSelectDescriptor(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_patterns.html'


class SliderSelectMultipleTextDescriptors(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_texts.html'

class SliderRadioSelectTextDescriptor(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_texts.html'


class SliderSelectMultipleNumbers(MatrixFilterMetaAppMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_numbers.html'

class SliderRadioSelectNumber(MatrixFilterMetaAppMixin, RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_numbers.html'


class SliderSelectMultipleTaxonfilters(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/slider_select_multiple_taxonfilters.html'

class SliderRadioSelectTaxonfilter(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/slider_select_multiple_taxonfilters.html'


'''
    END USER INPUT, no slider
'''
class SelectMultipleColors(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/select_multiple_colors.html'

class RadioSelectColor(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/select_multiple_colors.html'


class SelectMultipleDescriptors(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/select_multiple_patterns.html'

class RadioSelectDescriptor(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/select_multiple_patterns.html'


class SelectMultipleTextDescriptors(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/select_multiple_texts.html'

class RadioSelectTextDescriptor(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/select_multiple_texts.html'


class SelectMultipleNumbers(MatrixFilterMetaAppMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/select_multiple_numbers.html'

class RadioSelectNumber(MatrixFilterMetaAppMixin, RadioSelect):
    template_name = 'nature_guides/widgets/select_multiple_numbers.html'


class SelectMultipleTaxonfilters(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, SelectMultiple):
    template_name = 'nature_guides/widgets/select_multiple_taxonfilters.html'

class RadioSelectTaxonfilter(MatrixFilterMetaAppMixin, ChoiceExtraKwargsMixin, RadioSelect):
    template_name = 'nature_guides/widgets/select_multiple_taxonfilters.html'

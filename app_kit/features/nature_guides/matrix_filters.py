import base64
from django.utils.translation import gettext_lazy as _
from django import forms
from django.conf import settings
from django.templatetags.static import static

from django.contrib.contenttypes.models import ContentType

from .fields import RangeSpaceField, ObjectLabelModelMultipleChoiceField

from .widgets import (RangePropertyWidget, DefineRangeSpaceWidget, DefineDescriptionWidget, DefineColorsWidget,
                      DefineNumbersWidget,
                      SliderSelectMultipleColors, SliderSelectMultipleDescriptors, SliderRadioSelectDescriptor,
                      SliderRadioSelectColor, SliderSelectMultipleNumbers, SliderRadioSelectNumber,
                      SliderRadioSelectTaxonfilter, SliderSelectMultipleTaxonfilters,
                      SliderSelectMultipleTextDescriptors, SliderRadioSelectTextDescriptor,
                      DefineTextDescriptionWidget,
                      SelectMultipleColors, RadioSelectColor, SelectMultipleDescriptors, RadioSelectDescriptor,
                      SelectMultipleTextDescriptors, RadioSelectTextDescriptor, SelectMultipleNumbers,
                      RadioSelectNumber, SelectMultipleTaxonfilters, RadioSelectTaxonfilter)

from decimal import Decimal

from base64 import b64encode

import json, matplotlib

'''
    EVERYTHING IS A RANGE PARADIGM
    - several filter types exist
    - a trait needs an encoded_space which defines the allowed range of values
'''


'''
    MatrixFilter
    - always has a specific space
    - the space can be passed as
    --- encoded_space
    --- encoded_spaces_queryset
'''

MATRIX_FILTER_TYPES = (
    ('ColorFilter', _('Color filter')),
    ('RangeFilter', _('Range filter')),
    ('NumberFilter', _('Numbers filter')),
    ('DescriptiveTextAndImagesFilter', _('Descriptive text and images')),
    ('TaxonFilter', _('Taxonomic filter')),
    ('TextOnlyFilter', _('Text only filter')),
)



# MetaClass, extends a MatrixFilter class with FilterType-specific methods
class MatrixFilterType:

    # in the interface for creating matrix filters, an add space button is shown for multispace
    is_multispace = False

    # the form field class rendered for the end-user input
    MatrixSingleChoiceFormFieldClass = None
    MatrixMultipleChoiceFormFieldClass = None
    
    MatrixSingleChoiceWidgetClass = forms.Select
    MatrixMultipleChoiceWidgetClass = forms.CheckboxSelectMultiple


    # a form field for defining a valid space for a node
    NodeSpaceDefinitionFormFieldClass = None
    NodeSpaceDefinitionWidgetClass = None

    # e.g. color for ColorFilter
    verbose_space_name = None

    # these will be saved in the db automatically
    definition_parameters = ['identification_means']

    help_text = _("What is described by the filter, e.g. 'length of nose'")

    # filters are instantiated by passing in a MatrixFilter model instance: matrix_filter
    def __init__(self, matrix_filter):

        self.matrix_filter = matrix_filter

        # set encoded_space for the matrix_filter
        self.set_encoded_space()

        # check if the user allows the end-user to select multiple values 
        allow_multiple_values = False
        if self.matrix_filter.definition:
            allow_multiple_values = self.matrix_filter.definition.get('allow_multiple_values', False)

        if allow_multiple_values == True:
            self.MatrixFormFieldClass = self.MatrixMultipleChoiceFormFieldClass
            self.MatrixFormFieldWidget = self.MatrixMultipleChoiceWidgetClass

        else:
            self.MatrixFormFieldClass = self.MatrixSingleChoiceFormFieldClass
            self.MatrixFormFieldWidget = self.MatrixSingleChoiceWidgetClass

    ### DEFINITION
    def get_default_definition(self):
        return {}

    ''' never executed
    # make sure the definition is complete
    def set_definition(self, matrix_filter):

        if not matrix_filter.definition:
            default_definition = self.get_default_definition()
            matrix_filter.definition = default_definition

    '''
    
    ### ENCODED SPACE
    def get_empty_encoded_space(self):
        raise NotImplementedError('MatrixFilterType subclasses need a get_empty_encoded_space method')

    # make sure there is at least the empty space
    def set_encoded_space(self):
        raise NotImplementedError('MatrixFilterType subclasses need a set_encoded_space method')

    ### FORM FIELDS
    # the field displayed when end-user uses the identification matrix
    # the meta_app is required for making prepopulating the cache possible (ContentImageMixin requires MetaApp)
    def get_matrix_form_field(self, meta_app):
        raise NotImplementedError('MatrixFilterType subclasses need a get_matrix_form_field method')

    def get_matrix_form_field_widget(self, meta_app):

        allow_multiple_values = False

        if self.matrix_filter.definition:
            allow_multiple_values = self.matrix_filter.definition.get('allow_multiple_values', False)
        
        extra_context = {
            'matrix_filter_space_ctype' : ContentType.objects.get_for_model(self.matrix_filter.space_model),
            'allow_multiple_values' : allow_multiple_values,
        }
        widget = self.MatrixFormFieldWidget(meta_app, self.matrix_filter, extra_context=extra_context)
        return widget

    # the field when adding/editing a matrix node
    # display a field with min value, max value and units
    def get_node_space_widget_attrs(self):
        return {}
    
    def get_node_space_widget_args(self, meta_app):
        return []
    
    def get_node_space_widget_kwargs(self, from_url, **kwargs):
        show_add_button = kwargs.get('show_add_button', True)
        widget_kwargs = {
            'extra_context' : {
                'from_url' : from_url,
                'show_add_button' : show_add_button,
            },
            'attrs' : self.get_node_space_widget_attrs(),
        }
        return widget_kwargs


    def get_node_space_widget(self, meta_app, from_url, **kwargs):

        widget_kwargs = self.get_node_space_widget_kwargs(from_url, **kwargs)
        widget_args = self.get_node_space_widget_args(meta_app)
        widget = self.NodeSpaceDefinitionWidgetClass(*widget_args, **widget_kwargs)

        return widget

    
    def get_node_space_field_kwargs(self, meta_app, from_url, **kwargs):
        
        widget = self.get_node_space_widget(meta_app, from_url, **kwargs)
        
        field_kwargs = {
            'widget' : widget,
        }
        
        return field_kwargs

    
    def get_node_space_definition_form_field(self, meta_app, from_url, **kwargs):
        
        field_kwargs = self.get_node_space_field_kwargs(meta_app, from_url, **kwargs)        
        field = self.NodeSpaceDefinitionFormFieldClass(**field_kwargs)

        return field

    # in the ChildrenJsonCache, the (child)node's matrix filter values are stored as a list of values
    # receives a NodeFilterSpace instance or a MatrixFilterRestriction instance
    def get_filter_space_as_list(self, filter_space):
        raise NotImplementedError('MatrixFilterType subclasses require a get_filter_space_as_list method')


    def get_filter_space_as_list_with_identifiers(self, filter_space):
        raise NotImplementedError('MatrixFilterType subclasses require a get_filter_space_as_list_with_identifiers method')


    def get_space_identifier(self, space):
         raise NotImplementedError('MatrixFilterType subclasses require a get_space_identifier method')
    
    ### FORM DATA -> MatrixFilter instance
    # store definition and encoded_space
    # there are two types of form_data
    # A: data when the user defines the space depending on the parent_node (defining the trait)
    # B: data when the user assigns trait properties to a matrix entity
    # encode the value given from a form input
    # value can be a list

    # A, read a form and return an encoded_space. Only applies for Filters with is_multispace==False
    def get_encoded_space_from_form(self, form):
        raise NotImplementedError('MatrixFilterType subclasses need a encoded_space_from_form method')

    # B, can have multiple values
    # executed when a nodelink is saved, field is get_node_space_definition_form_field
    def encode_entity_form_value(self, form_value):
        raise NotImplementedError('MatrixFilterType subclasses need a encode_entity_form_value method')

    ### SAVE A SINGLE SPACE (is_multispace == True)
    def save_single_space(self, form):
        if self.is_multispace == True:
            raise NotImplementedError('Multispace MatrixFilterType subclasses need a save_single_space method')
        else:
            raise TypeError('Only Multispace MatrixFilterType subclasses can use the save_single_space method')

    ### MATRIX_FILTER_INSTANCE -> FORM DATA
    # if is_multispace==False, the encoded space can be decoded in key:value pairs
    def get_space_initial(self):
        raise NotImplementedError('MatrixFilterType subclasses need a get_space_initial method')

    def get_single_space_initial(self, matrix_filter_space):
        if self.is_multispace == True:
            raise NotImplementedError('Multispace MatrixFilterType subclasses need a get_single_space_initial method')
        else:
            raise TypeError('Only Multispace MatrixFilterType subclasses can use the get_single_space_initial method')


    # VALIDATION
    def validate_encoded_space(self, space):
        raise NotImplementedError('MatrixFilterType subclasses need a validate_encoded_space method')


'''
    Only one MatrixFilterSpace exists for this MatrixFilter AND
    the encoded space of this one MatrixFilterSpace is the encoded space
    of the MatrixFilter
'''
class SingleSpaceFilterMixin:

    def set_encoded_space(self):
        matrix_filter_space = self.matrix_filter.get_space().first()

        if matrix_filter_space:
            self.matrix_filter.encoded_space = matrix_filter_space.encoded_space
        else:
            self.matrix_filter.encoded_space = self.get_empty_encoded_space()


    def get_filter_space_as_list_with_identifiers(self, filter_space):

        space_list = self.get_filter_space_as_list(filter_space)

        space_list_with_identifiers = []

        for encoded_space in space_list:
            space_identifier = self.get_space_identifier(encoded_space)

            space_json = {
                'spaceIdentifier' : space_identifier,
                'encodedSpace' : encoded_space,
            }

            space_list_with_identifiers.append(space_json)
        
        return space_list_with_identifiers


    def get_space_identifier(self, encoded_space):

        space_str = json.dumps(encoded_space, separators=(',', ':'))
        space_b64 = base64.b64encode(space_str.encode('utf-8')).decode('utf-8')
        space_identifier = '{0}:{1}'.format(str(self.matrix_filter.uuid), space_b64)

        return space_identifier


class MultiSpaceFilterMixin:

    def encode_entity_form_value(self, form_value):
        raise NotImplementedError('{0} is a multispatial filter and cant encode single form values'.format(
            self.__class__.__name__))


    def get_empty_encoded_space(self):
        return []

    def set_encoded_space(self):
        
        self.matrix_filter.encoded_space = self.get_empty_encoded_space()
        
        matrix_filter_spaces = self.matrix_filter.get_space()

        if matrix_filter_spaces:
            
            for space in matrix_filter_spaces:
                self.matrix_filter.encoded_space.append(space.encoded_space)


    def get_filter_space_as_list_with_identifiers(self, filter_space):

        space_list_with_identifiers = []

        for space in filter_space.values.all():

            space_identifier = self.get_space_identifier(space)

            space_json = {
                'spaceIdentifier' : space_identifier,
                'encodedSpace' : space.encoded_space,
            }

            space_list_with_identifiers.append(space_json)
        
        return space_list_with_identifiers


    def get_space_identifier(self, space):

        space_identifier = '{0}:{1}'.format(str(self.matrix_filter.uuid), str(space.id))

        return space_identifier
        

'''
    RangeFilter
    - encoded: [0,10]
'''
class RangeFilter(SingleSpaceFilterMixin, MatrixFilterType):

    verbose_name = _('Range filter')
    definition_parameters = ['identification_means', 'step', 'unit', 'unit_verbose', 'tolerance']

    help_text = _("What is described by this trait, e.g. 'length of nose'")

    MatrixSingleChoiceFormFieldClass = forms.DecimalField
    MatrixMultipleChoiceFormFieldClass = forms.DecimalField

    MatrixSingleChoiceWidgetClass = RangePropertyWidget
    MatrixMultipleChoiceWidgetClass = RangePropertyWidget

    NodeSpaceDefinitionFormFieldClass = RangeSpaceField
    NodeSpaceDefinitionWidgetClass = DefineRangeSpaceWidget

    def get_default_definition(self):
        definition = {
            'step' : 1,
            'unit' : '',
            'unit_verbose' : '',
        }

        return definition


    def get_empty_encoded_space(self):
        return [0,0]

    # field for the end-user input
    def get_matrix_form_field(self, meta_app):
        # decimalfield as a slider
        widget = self.get_matrix_form_field_widget(meta_app)
        
        return self.MatrixFormFieldClass(required=False, label=self.matrix_filter.name,
                    min_value=self.matrix_filter.encoded_space[0], max_value=self.matrix_filter.encoded_space[1],
                    decimal_places=None, widget=widget)


    # display a field with min value, max value and units
    def get_node_space_field_kwargs(self, meta_app, from_url, **kwargs):

        field_kwargs = super().get_node_space_field_kwargs(meta_app, from_url, **kwargs)
        
        field_kwargs.update({
            'subfield_kwargs' : {
                'decimal_places' : None,
            }
        })
    
        return field_kwargs


    def get_node_space_widget_kwargs(self, from_url, **kwargs):

        widget_kwargs = super().get_node_space_widget_kwargs(from_url, **kwargs)

        if self.matrix_filter.definition:
            unit = self.matrix_filter.definition.get('unit', '')
        else:
            unit = ''

        widget_kwargs['extra_context'].update({
            'unit' : unit,
        })
        
        return widget_kwargs
    

    def get_node_space_widget_attrs(self):

        if self.matrix_filter.definition:
            
            step =  self.matrix_filter.definition.get('step', 1)
        else:
            step = 1
            
        widget_attrs = {
            'step' : step,
        }
        return widget_attrs

    # ENCODE FORM VALUES TO ENCODED SPACES
    # A
    def get_encoded_space_from_form(self, form):
        encoded_space = [form.cleaned_data['min_value'], form.cleaned_data['max_value']]
        return encoded_space

    # the form field (RangeSpaceField) already produces [min,max]
    def encode_entity_form_value(self, form_value):
        return form_value

    # FILL FORMS
    # get initial for form
    def get_space_initial(self):

        space_initial = {}

        if self.matrix_filter.encoded_space:
            
            space_initial = {
                'min_value' : self.matrix_filter.encoded_space[0],
                'max_value' : self.matrix_filter.encoded_space[1]
            }
            
        return space_initial


    # node/restriction filter space as list
    def get_filter_space_as_list(self, filter_space):
        # range filter stores [min,max] as encoded space
        # a list of spaces is expected, so wrap the range in a list
        return [filter_space.encoded_space]


    def validate_encoded_space(self, space):

        is_valid = True

        if isinstance(space, list) and len(space) == 2:

            for parameter in space:
                if isinstance(parameter, int) or isinstance(parameter, float):
                    continue
                else:
                    is_valid = False
                    break
            
        else:
            is_valid = False

        return is_valid
        

'''
    NumberFilter
    - one set of numbers, not multiple sets of numbers, sets can always be unioned/merged
    - encoded: [2,3.5,4,8]
'''

class NumberFilter(SingleSpaceFilterMixin, MatrixFilterType):

    verbose_name = _('Number filter')
    definition_parameters = ['identification_means', 'unit', 'unit_verbose']

    help_text = _("What is described by this trait, e.g. 'number of legs'")
    
    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixSingleChoiceWidgetClass = RadioSelectNumber
    MatrixMultipleChoiceWidgetClass = SelectMultipleNumbers
    
    NodeSpaceDefinitionFormFieldClass = forms.MultipleChoiceField
    NodeSpaceDefinitionWidgetClass = DefineNumbersWidget

    def get_default_definition(self):
        definition = {
            'unit' : '',
        }

        return definition

    def get_empty_encoded_space(self):
        return []            

    def _strip(self, number_str):
        if '.' in number_str:
            number_str = number_str.rstrip('0').rstrip('.')

        return number_str

    def _get_choices(self):
        
        choices = []
        for number in self.matrix_filter.encoded_space:
            choices.append((self._strip(str(number)), self._strip(str(number))))

        return choices

    # FORM FIELDS
    def get_matrix_form_field(self, meta_app):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget(meta_app)
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)
    

    def get_node_space_field_kwargs(self, meta_app, from_url, **kwargs):

        field_kwargs = super().get_node_space_field_kwargs(meta_app, from_url, **kwargs)
        field_kwargs.update({
            'choices' : self._get_choices(),
        })
        return field_kwargs

    # ENCODE FORM VALUES TO ENCODED SPACES
    # A, exepcts numbers as a list [1,2,3]
    def get_encoded_space_from_form(self, form):
        numbers = [float(i) for i in form.cleaned_data['numbers']]
        numbers.sort()
        return numbers

    # B, expects numbers as a list [1,2,3]
    def encode_entity_form_value(self, form_value):
        numbers = [float(i) for i in form_value]
        numbers.sort()
        return numbers

    # FILL FORMS
    # get initial for form
    def get_space_initial(self):
        formatted = ['{0:g}'.format(number) for number in self.matrix_filter.encoded_space]
        space_initial = {
            'numbers' : ','.join(formatted)
        }
        return space_initial


    # node/restriction filter space as list
    def get_filter_space_as_list(self, filter_space):
        # number filter stores [x,y,z] as encoded space
        return filter_space.encoded_space

    def validate_encoded_space(self, space):

        is_valid = True
        
        if isinstance(space, list):
            for number in space:
                if isinstance(number, int) or isinstance(number, float):
                    continue
                else:
                    is_valid = False
                    break
        else:
            is_valid = False

        return is_valid

    # subspace is a single number
    def get_space_identifier(self, number):

        space_identifier = '{0}:{1}'.format(str(self.matrix_filter.uuid), str(number))

        return space_identifier


'''
    ColorFilter
    - one MatrixFilterSpace entry for one color - this enables editing one single color
    - encoded_space [r,g,b,a]
'''
class ColorFilter(MultiSpaceFilterMixin, MatrixFilterType):

    is_multispace = True

    definition_parameters = ['identification_means', 'allow_multiple_values']

    verbose_name = _('Color filter')
    verbose_space_name = _('color')

    help_text = _("What is described by this trait, e.g. 'fur color'")

    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixSingleChoiceWidgetClass = RadioSelectColor
    MatrixMultipleChoiceWidgetClass = SelectMultipleColors
    
    NodeSpaceDefinitionFormFieldClass = ObjectLabelModelMultipleChoiceField
    NodeSpaceDefinitionWidgetClass = DefineColorsWidget


    # COLOR ENCODING CONVERSION
    # transform hex values #RRGGBB or #RRGGBBAA to the encoded form [r,g,b,a]
    # OR a list of rgba colors [[r,g,b,a],[r,g,b,a]]
    def encode_from_hex(self, value):
        """Return (red, green, blue) for the color given as #rrggbbaa or rrggbb."""
        value = value.lstrip('#')

        # encoded len is always 4, including alpha channel
        if len(value) == 6:
            lv = len(value)
            encoded_color = [int(value[i:i+2], 16) for i in (0, 2 ,4)] + [1]
        elif len(value) == 8:
            encoded_color = [int(value[i:i+2], 16) for i in (0, 2 ,4)] + [round(float(int(value[6:8],16)/255),2)]
        else:
            raise ValueError('hex color has to be in the format #RRGGBB or #RRGGBBAA')

        return encoded_color


    def encoded_space_to_hex(self, encoded_space):
        # print(encoded_space)
        return self.rgb_to_hex(encoded_space[0], encoded_space[1], encoded_space[2], encoded_space[3])
        

    def rgb_to_hex(self, r, g, b, a=None):
        """Return color as #rrggbb for the given color values."""
        color_hex = '#%02x%02x%02x' % (r, g, b)
        
        if a is not None:
            # a is a percentage between 0.0 and 1.0
            # decimal = percentage * 255, percentage as float
            # convert decimal to hexadecimal value . ex: 127.5 in decimal = 7*16ˆ1 + 15 = 7F in hexadecimal

            #alpha_decimal = a * 255
            #alpha_hex = hex(alpha_decimal).split('x')[-1]

            color = (r/255, g/255, b/255, a)
            
            #color_hex = '{0}{1}'.format(color_hex, alpha_hex)
            color_hex = matplotlib.colors.to_hex(color, keep_alpha=True)
            
        return color_hex


    def list_to_rgba_str(self, rgba_list):
        r = rgba_list[0]
        g = rgba_list[1]
        b = rgba_list[2]
        a = 1
        
        if len(rgba_list) >= 4:
            a = rgba_list[3]
        
        rgba_str = 'rgba({0},{1},{2},{3})'.format(r,g,b,a)

        return rgba_str
        
    # encoded space can be [r,g,b,a] or [[r,g,b,a], [r,g,b,a]]
    def encoded_space_to_html(self, encoded_space):

        if isinstance(encoded_space[0], list):
            gradient_colors = []
            for color in encoded_space:
                rgba_str = self.list_to_rgba_str(color)
                gradient_colors.append(rgba_str)

            if len(encoded_space) == 2:
                html = 'linear-gradient(to right, {0})'.format(','.join(gradient_colors))
            else:
                html = 'linear-gradient(to right, {0}, {0} 33%, {1} 33%, {1} 66%, {2} 66%, {2} 100%)'.format(gradient_colors[0], gradient_colors[1], gradient_colors[2])
        else:
            html = self.list_to_rgba_str(encoded_space)

        return html

    def decode(self, encoded_space):
        return self.encoded_space_to_html(encoded_space)

    def _get_choices(self):

        choices = []

        for space in self.matrix_filter.get_space():

            description = None
            color_type = 'single'

            if space.additional_information:
                description = space.additional_information.get('description', None)

                if 'color_type' in space.additional_information:
                    color_type = space.additional_information['color_type']
                else:
                    # fallback for older colors
                    gradient = space.additional_information.get('gradient', False)
                    if gradient:
                        color_type = 'gradient'

            encoded_space = space.encoded_space

            # r,g,b,a
            # it should becomde something like [255,255,255,1], NOT [255, 255, 255, 1]
            # spaces dhould be prevented because javascript JSON.stringify() does not use  spaces and values from
            # javascript and python sometimes have to be comapred as strings
            choice_value = json.dumps(encoded_space, separators=(',', ':'))
            space_html = self.encoded_space_to_html(encoded_space)

            extra_kwargs = {
                'modify' : True,
                'space_id' : space.id,
                'description' : description,
                'color_type' : color_type,
            }

            choice = (choice_value, space_html, extra_kwargs)
            
            choices.append(choice)

        return choices

    def get_matrix_form_field(self, meta_app):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget(meta_app)
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)


    def get_node_space_widget_args(self, meta_app):
        return [meta_app, self]
    
    # node space definition: assign colors to a node (child)
    def get_node_space_definition_form_field(self, meta_app, from_url, **kwargs):
        queryset = self.matrix_filter.get_space()

        field_kwargs = self.get_node_space_field_kwargs(meta_app, from_url, **kwargs)
        
        field = self.NodeSpaceDefinitionFormFieldClass(queryset, **field_kwargs)

        return field

    # READ FORMS
    # ColorFilter is multispatial
    def get_encoded_space_from_form(self, form):
        return []

    # FILL FORMS
    # ColorFilter is multispace, spaces are added using a separate form
    def get_space_initial(self):
        return {}

    # initial for the html color fields (color, color_2), description and gradient
    def get_single_space_initial(self, matrix_filter_space):

        encoded_space = matrix_filter_space.encoded_space

        if isinstance(encoded_space[0], list):
            color_hex = self.encoded_space_to_hex(encoded_space[0])
            color_2_hex = self.encoded_space_to_hex(encoded_space[1])
            if len(encoded_space) == 3:
                color_3_hex = self.encoded_space_to_hex(encoded_space[2])

        else:
            color_hex = self.encoded_space_to_hex(matrix_filter_space.encoded_space)

        # currently, the html color input does not support alpha channels, respect leading #
        if len(color_hex) > 7:
            color_hex = color_hex[:7]

        initial_colortype = 'single'
        
        initial = {
            'color' : color_hex,
            'color_type': initial_colortype
        }

        if matrix_filter_space.additional_information:
            description = matrix_filter_space.additional_information.get('description', None)
            if description:
                initial['description'] = description

            color_type = matrix_filter_space.additional_information.get('color_type', 'single')
            initial['color_type'] = color_type

            if color_type == 'gradient':
                initial['color_2'] = color_2_hex[:7]
            elif color_type == 'triplet':
                initial['color_2'] = color_2_hex[:7]
                initial['color_3'] = color_3_hex[:7]
        
        return initial

    ### SAVE ONE COLOR
    # this has to trigger update_value in childrenjson manager
    def save_single_space(self, form):

        MatrixFilterSpace = self.matrix_filter.space_model

        matrix_filter_space_id = form.cleaned_data.get('matrix_filter_space_id', None)
        if matrix_filter_space_id:
            space = MatrixFilterSpace.objects.get(pk=form.cleaned_data['matrix_filter_space_id'])
            old_encoded_space = space.encoded_space
        else:
            space = MatrixFilterSpace(
                matrix_filter = self.matrix_filter,
            )
            old_encoded_space = None

        # save description and gradient
        if not space.additional_information:
            space.additional_information = {}
            
        description = form.cleaned_data.get('description', None)
        color_type = form.cleaned_data.get('color_type', 'single')

        space.additional_information['color_type'] = color_type
        
        if description:
            space.additional_information['description'] = description
        else:
            if 'description' in space.additional_information:
                del space.additional_information['description']

        # put the color into the encoded space
        color_1_hex_value = form.cleaned_data['color']
        encoded_space = self.encode_from_hex(color_1_hex_value)

        color_2_hex_value = form.cleaned_data.get('color_2', None)
        color_3_hex_value = form.cleaned_data.get('color_3', None)

        if color_type == 'gradient' and color_2_hex_value:
            encoded_color_2 = self.encode_from_hex(color_2_hex_value)
            encoded_space = [encoded_space, encoded_color_2]

        elif color_type == 'triplet' and color_2_hex_value and color_3_hex_value:
            encoded_color_2 = self.encode_from_hex(color_2_hex_value)
            encoded_color_3 = self.encode_from_hex(color_3_hex_value)
            encoded_space = [encoded_space, encoded_color_2, encoded_color_3]

        space.encoded_space = encoded_space
        space.save(old_encoded_space=old_encoded_space)

        return space


    # node/restriction filter space as list
    def get_filter_space_as_list(self, filter_space):
        # return a list of 4-tuples
        space_list = []

        for space in filter_space.values.all():
            space_list.append(space.encoded_space)
            
        return space_list


    # color as a list : [r,g,b,a]
    def validate_single_color(left, color_as_list):

        is_valid = True

        if isinstance(color_as_list, list):
        
            if len(color_as_list) == 4:
            
                r = color_as_list[0]
                g = color_as_list[1]
                b = color_as_list[2]
                a = color_as_list[3]

                for parameter in [r,g,b]:
                    if not isinstance(parameter, int):
                        is_valid = False
                        break

                    if parameter < 0 or parameter > 255:
                        is_valid = False
                        break

                if isinstance(a, float) or isinstance(a, int):
                    if a < 0 or a > 1:
                        is_valid = False
                        
                else:
                    is_valid = False

            else:
                is_valid = False

        else:
            is_valid = False

        return is_valid
            
                    
    def validate_encoded_space(self, space):
        
        is_valid = True
        
        #[r,g,b,a]
        if isinstance(space, list) and len(space) > 0:

            if isinstance(space[0], list):

                for color in space:
                    is_valid = self.validate_single_color(color)
                    if is_valid == False:
                        break
            else:
                is_valid = self.validate_single_color(space)
                    
        else:
            is_valid = False

        return is_valid


'''
    DescriptiveTextAndImages Filter
'''

'''
    Multidimensional Descriptor
    - = elements of its Space
    - image should be an AppContentImage instance
'''

class DescriptiveTextAndImagesFilter(MultiSpaceFilterMixin, MatrixFilterType):

    is_multispace = True

    definition_parameters = ['identification_means', 'allow_multiple_values']

    verbose_name = _('Text/Images filter')
    verbose_space_name = _('text with image')

    help_text = _("What is described by this trait, e.g. 'leaf shape'")
    
    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixSingleChoiceWidgetClass = RadioSelectDescriptor
    MatrixMultipleChoiceWidgetClass = SelectMultipleDescriptors
    
    NodeSpaceDefinitionFormFieldClass = ObjectLabelModelMultipleChoiceField
    NodeSpaceDefinitionWidgetClass = DefineDescriptionWidget

    def get_default_definition(self):
        return {}

    def _get_choices(self):
        
        choices = []

        for space in self.matrix_filter.get_space():

            image = None

            extra_kwargs = {
                'image' : image,
                'modify' : True,
                'space_id' : space.id,
                'matrix_filter_space' : space,
            }

            image = space.image()
            if image and image.image_store.source_image:
                extra_kwargs['image'] = image
            
            choices.append((space.encoded_space, space.encoded_space, extra_kwargs))

        return choices

    def get_matrix_form_field(self, meta_app):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget(meta_app)
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)


    def get_node_space_widget_args(self, meta_app):
        return [meta_app, self]
    
    '''
    this method needs a queryset in the space as it works with ModelMultipleChoiceField
    '''
    def get_node_space_definition_form_field(self, meta_app, from_url, **kwargs):
        queryset = self.matrix_filter.get_space()

        field_kwargs = self.get_node_space_field_kwargs(meta_app, from_url, **kwargs)
        
        return self.NodeSpaceDefinitionFormFieldClass(queryset, **field_kwargs)


    # READ FORMS
    # TextAndImages is multispatial, the form encodes the space during its save() method
    def get_encoded_space_from_form(self, form):
        return []

    # FILL FORMS
    # get initial for form
    def get_space_initial(self):
        return {}


    def get_single_space_initial(self, matrix_filter_space):

        initial = {
            'text' : matrix_filter_space.encoded_space,
        }
        return initial


    ### SAVE ONE Text with image
    def save_single_space(self, form):
        MatrixFilterSpace = self.matrix_filter.space_model

        matrix_filter_space_id = form.cleaned_data.get('matrix_filter_space_id', None)
        if matrix_filter_space_id:
            space = MatrixFilterSpace.objects.get(pk=form.cleaned_data['matrix_filter_space_id'])
            old_encoded_space = space.encoded_space
        else:
            space = MatrixFilterSpace(
                matrix_filter = self.matrix_filter,
            )
            old_encoded_space = None

        # the text is the encoded space
        space.encoded_space = form.cleaned_data['text']
        space.save(old_encoded_space=old_encoded_space)

        return space


    # node filter space as list
    def get_filter_space_as_list(self, filter_space):
        space_list = []
        for space in filter_space.values.all():
            space_list.append(space.encoded_space)
        return space_list


    def validate_encoded_space(self, space):
        if not isinstance(space, str):
            return False

        return True


'''
    Text only filter
    - no images, for longer texts
'''

class TextOnlyFilter(MultiSpaceFilterMixin, MatrixFilterType):

    is_multispace = True

    definition_parameters = ['identification_means', 'allow_multiple_values']

    verbose_name = _('Text only filter')
    verbose_space_name = _('text')

    help_text = _("What is described by this trait, e.g. 'leaf shape'")
    
    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixSingleChoiceWidgetClass = RadioSelectTextDescriptor
    MatrixMultipleChoiceWidgetClass = SelectMultipleTextDescriptors
    
    NodeSpaceDefinitionFormFieldClass = ObjectLabelModelMultipleChoiceField
    NodeSpaceDefinitionWidgetClass = DefineTextDescriptionWidget


    ### FORM FIELDS
    # the field displayed when end-user uses the identification matrix
    def _get_choices(self):
        
        choices = []

        for space in self.matrix_filter.get_space():

            extra_kwargs = {
                'modify' : True,
                'space_id' : space.id,
            }
            
            choices.append((space.encoded_space, space.encoded_space, extra_kwargs))

        return choices

    def get_matrix_form_field(self, meta_app):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget(meta_app)
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)


    
    ### FORM DATA -> MatrixFilter instance
    # store definition and encoded_space
    # there are two types of form_data
    # A: data when the user defines the space depending on the parent_node (defining the trait)
    # B: data when the user assigns trait properties to a matrix entity
    # encode the value given from a form input
    # value can be a list


    # READ FORMS
    # TextAndImages is multispatial, the form encodes the space during its save() method
    def get_encoded_space_from_form(self, form):
        return []

    # FILL FORMS
    # get initial for form
    def get_space_initial(self):
        return {}


    def get_single_space_initial(self, matrix_filter_space):

        initial = {
            'text' : matrix_filter_space.encoded_space,
        }
        return initial

    ### SAVE A SINGLE SPACE (is_multispace == True)
    def save_single_space(self, form):
        MatrixFilterSpace = self.matrix_filter.space_model

        matrix_filter_space_id = form.cleaned_data.get('matrix_filter_space_id', None)
        if matrix_filter_space_id:
            space = MatrixFilterSpace.objects.get(pk=form.cleaned_data['matrix_filter_space_id'])
            old_encoded_space = space.encoded_space
        else:
            space = MatrixFilterSpace(
                matrix_filter = self.matrix_filter,
            )
            old_encoded_space = None

        # the text is the encoded space
        space.encoded_space = form.cleaned_data['text']
        space.save(old_encoded_space=old_encoded_space)

        return space


    def get_node_space_widget_args(self, meta_app):
        return [meta_app, self]
    
    
    def get_node_space_definition_form_field(self, meta_app, from_url, **kwargs):
        queryset = self.matrix_filter.get_space()

        field_kwargs = self.get_node_space_field_kwargs(meta_app, from_url, **kwargs)
        
        return self.NodeSpaceDefinitionFormFieldClass(queryset, **field_kwargs)


    # node filter space as list
    def get_filter_space_as_list(self, filter_space):
        space_list = []
        for space in filter_space.values.all():
            space_list.append(space.encoded_space)
        return space_list
    

    # VALIDATION
    def validate_encoded_space(self, space):
        if not isinstance(space, str):
            return False

        return True
    

'''
    Taxonomic filtering
    - uses nuids to detect descendants
    - there are predefined filters
'''
from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon

PREDEFINED_TAXONOMIC_FILTERS = (
    ('Animalia', _('Animals')),
    ('Plantae', _('Plants')),
    ('Fungi', _('Mushrooms')),
    ('Chordata', _('Chordates')),
    ('Mammalia', _('Mammals')),
    ('Aves', _('Birds')),
    ('Amphibia', _('Amphibians')),
    ('Anura', _('Frogs')),
    ('Holocephali,Elasmobranchii,Sarcopterygii,Actinopterygii', _('Fish')),
    ('Arthropoda', _('Arthropods')),
    ('Insecta', _('Insects')),
    ('Lepidoptera', _('Butterflies')),
    ('Coleoptera', _('Bugs')),
    ('Odonata', _('Dragonflies and damselflies')),
    ('Arachnida', _('Spiders')),
    ('Mollusca', _('Molluscs')),
)

PREDEFINED_FILTER_LATNAMES = [predefined[0] for predefined in PREDEFINED_TAXONOMIC_FILTERS]

class TaxonFilter(SingleSpaceFilterMixin, MatrixFilterType):

    is_multispace = False

    definition_parameters = ['identification_means']

    verbose_name = _('Taxonomic Filter')
    verbose_space_name = _('Taxon')

    help_text = _("Something like 'tree genus' or 'taxonomic classification' ")
    
    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixSingleChoiceWidgetClass = RadioSelectTaxonfilter
    MatrixMultipleChoiceWidgetClass = SelectMultipleTaxonfilters
    
    NodeSpaceDefinitionFormFieldClass = None # works automatically, no definition required
    NodeSpaceDefinitionFormFieldWidget = None # works automatically, no definition required

    def get_default_definition(self):
        return {}

    def get_empty_encoded_space(self):
        return []

    # END-USER MATRIX FORM FIELD
    def _get_choices(self):

        choices = []

        if self.matrix_filter.encoded_space:

            for taxonfilter in self.matrix_filter.encoded_space:
                # example taxon filter: 
                # {"taxa": [{"taxon_nuid": "001", "name_uuid": "f61b30e9-90d3-4e87-9641-eee71506aada",
                # "taxon_source": "taxonomy.sources.col", "taxon_latname": "Animalia", "taxon_author":None}],"latname": "Animalia",
                # "is_custom": false}

                taxonfilter_json = json.dumps(taxonfilter, separators=(',', ':'))
                
                extra_kwargs = {
                    'image' : static('app_kit/buttons/taxonfilters/{0}.svg'.format(taxonfilter['latname']) ),
                    'is_custom' : taxonfilter['is_custom'],
                    'data_value' : taxonfilter,
                    'data_b64value' : b64encode(taxonfilter_json.encode('utf-8')).decode('utf-8'),
                }

                value = taxonfilter['latname']
                label = taxonfilter['latname']
                
                choices.append((value, label, extra_kwargs))

        # sort by latin name
        choices.sort(key=lambda choice: choice[0])

        return choices
    

    def get_matrix_form_field(self, meta_app):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget(meta_app)
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)

    # READ FORMS

    def make_taxonfilter_taxon(self, lazy_taxon):
        taxonfilter_taxon = {
            'taxon_source' : lazy_taxon.taxon_source,
            'taxon_latname' : lazy_taxon.taxon_latname,
            'taxon_author' : lazy_taxon.taxon_author,
            'name_uuid' : lazy_taxon.name_uuid,
            'taxon_nuid' : lazy_taxon.taxon_nuid,
        }

        return taxonfilter_taxon
    

    def make_taxonfilter_entry(self, latname, sources):

        # latname can be comma separated
        is_custom = False

        if latname not in PREDEFINED_FILTER_LATNAMES:
            is_custom = True
        
        entry = {
            'latname': latname, # overarching latname for the filter
            'taxa' : [],
            'is_custom' : is_custom,
        }

        for source in sources:
            models = TaxonomyModelRouter(source)

            latnames = latname.split(',')

            for latname in latnames:
                taxon = models.TaxonTreeModel.objects.filter(taxon_latname=latname).first()
                if taxon:
                    lazy_taxon = LazyTaxon(instance=taxon)
                    taxon_entry = self.make_taxonfilter_taxon(lazy_taxon)
                    if taxon_entry not in entry['taxa']:
                        entry['taxa'].append(taxon_entry)

        return entry
    
    
    def get_encoded_space_from_form(self, form):
        # the form contains a list of taxa as latnames
        encoded_space = []
        
        all_sources = [source[0] for source in settings.TAXONOMY_DATABASES]

        # form.cleaned_data['taxonomic_filters'] can contain custom filters
        for latname in form.cleaned_data['taxonomic_filters']:

            # first, work the predefined taxonomic filters
            if latname in PREDEFINED_FILTER_LATNAMES:
                entry = self.make_taxonfilter_entry(latname, all_sources)
                encoded_space.append(entry)

            else:
                # use the custom filter entry from the old encoded space
                for taxonfilter in self.matrix_filter.encoded_space:
                    if taxonfilter['is_custom'] == True and taxonfilter['latname'] == latname:
                        encoded_space.append(taxonfilter)

        # save the custom taxonomic filter if any
        custom_taxon = form.cleaned_data['add_custom_taxonomic_filter']
        if custom_taxon:

            # use the supplied taxon, only search other taxonomies
            remaining_sources = list(all_sources)
            del remaining_sources[remaining_sources.index(custom_taxon.taxon_source)]
            
            entry = self.make_taxonfilter_entry(custom_taxon.taxon_latname, remaining_sources)

            # add the already supplied taxon to the filter
            custom_taxon_entry = self.make_taxonfilter_taxon(custom_taxon)
            entry['taxa'].append(custom_taxon_entry)
            entry['is_custom'] = True
            encoded_space.append(entry)
            
        return encoded_space

    # FILL FORMS
    # get initial for form
    def get_space_initial(self):
        initial = {}
        # add the predefined filters of this nature guide to initial
        existing = self.matrix_filter.encoded_space
        initial['taxonomic_filters'] = [f['latname'] for f in existing]
        
        return initial

    # no node space definition for taxon filter
    def get_node_space_definition_form_field(self, meta_app, from_url, **kwargs):
        return None

    def get_node_space_widget_kwargs(self, from_url, **kwargs):
        return {}

    def get_node_space_widget(self, meta_app, from_url, **kwargs):
        return None

    def get_node_space_field_kwargs(self, meta_app, from_url, **kwargs):
        return {}

    def get_filter_space_as_list(self, filter_space):
        raise NotImplementedError('TaxonFilter does not support get_filter_space_as_list. Use get_space_for_node instead.')

    def get_filter_space_as_list_with_identifiers(self, filter_space):
        raise NotImplementedError('TaxonFilter does not support get_filter_space_as_list_with_identifiers. Use get_space_for_node_with_identifier instead.')
    # a node only provides the nuid, which is sufficient
    '''
    [{
      "taxa": [
        {
          "name_uuid": "151d41f5-5941-4169-b77b-175ab0876ca6",
          "taxon_nuid": "006",
          "taxon_author": null,
          "taxon_source": "taxonomy.sources.col",
          "taxon_latname": "Plantae"
        },
        {
          "name_uuid": "c303f1b7-feec-45cd-b615-f0773ced2107",
          "taxon_nuid": "003",
          "taxon_author": "admin",
          "taxon_source": "taxonomy.sources.custom",
          "taxon_latname": "Plantae"
        }
      ],
      "latname": "Plantae",
      "is_custom": false
    }]
    '''
    # this is for making space_identifiers in javascript work
    # you do not have to compare nuids during runtime, this can be done during the build process, or in the backend (appkit)
    def get_space_for_node(self, node):

        node_space = []
        
        if (node.meta_node.taxon):
            node_taxon = node.meta_node.taxon
            
            if self.matrix_filter.encoded_space:

                for taxon_filter in self.matrix_filter.encoded_space:

                    is_valid = False

                    for taxon in taxon_filter['taxa']:
                    
                        if node_taxon.taxon_source == taxon['taxon_source'] and node_taxon.taxon_nuid.startswith(taxon['taxon_nuid']):
                            is_valid = True
                            break

                    if is_valid == True:
                        node_space.append(taxon_filter)
        
        return node_space

    def get_space_for_node_with_identifiers(self, node):

        space_list_with_identifiers = []

        node_space = self.get_space_for_node(node)

        # taxonfilter is an encoded subspace (python dict, describing taxa)
        for taxonfilter in node_space:

            space_identifier = self.get_space_identifier(taxonfilter)

            space_b64 = self.get_taxonfilter_space_b64(taxonfilter)

            space_json = {
                'spaceIdentifier' : space_identifier,
                'encodedSpace' : space_b64
            }

            space_list_with_identifiers.append(space_json)
        
        return space_list_with_identifiers


    def get_taxonfilter_space_b64(self, subspace):
        space_b64 = base64.b64encode(json.dumps(subspace, separators=(',', ':')).encode('utf-8')).decode('utf-8')

        return space_b64


    def get_space_identifier(self, taxonfilter):

        name = taxonfilter['latname']
        space_identifier = '{0}:{1}'.format(str(self.matrix_filter.uuid), name)

        return space_identifier


    # taxon json
    #{"taxa": [{"taxon_nuid": "001", "name_uuid": "f61b30e9-90d3-4e87-9641-eee71506aada",
    # "taxon_source": "taxonomy.sources.col", "taxon_latname": "Animalia", "taxon_author":None}],"latname": "Animalia",
    # "is_custom": false}
    def validate_encoded_space(self, space):

        is_valid = True


        if isinstance(space, list):

            for taxonfilter in space:
                
                if isinstance(taxonfilter, dict):

                    if 'taxa' in taxonfilter and 'latname' in taxonfilter and type(taxonfilter['latname']) == str and 'is_custom' in taxonfilter and type(taxonfilter['is_custom']) == bool:

                        for taxon in taxonfilter['taxa']:

                            if isinstance(taxon, dict):

                                if not 'taxon_source' in taxon or not isinstance(taxon['taxon_source'], str):
                                    is_valid = False
                                    break

                                elif not 'taxon_latname' in taxon or not isinstance(taxon['taxon_latname'], str):
                                    is_valid = False
                                    break

                                # authr can be None, has to be in taxon
                                elif not 'taxon_author' in taxon:
                                    is_valid = False
                                    break

                                elif not 'name_uuid' in taxon or not isinstance(taxon['name_uuid'], str):
                                    is_valid = False
                                    break

                                elif not 'taxon_nuid' in taxon or not isinstance(taxon['taxon_nuid'], str):
                                    is_valid = False
                                    break

                            else:
                                is_valid = False
                                break
                            
                    else:
                        is_valid = False

                else:
                    is_valid = False

        else:
            is_valid = False

        return is_valid

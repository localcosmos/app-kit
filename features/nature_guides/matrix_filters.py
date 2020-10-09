from django.utils.translation import gettext_lazy as _
from django import forms
from django.conf import settings
from django.templatetags.static import static

from django.contrib.contenttypes.models import ContentType

from .fields import RangeSpaceField, ObjectLabelModelMultipleChoiceField

from .widgets import (RangePropertyWidget, DefineRangeSpaceWidget, DefineDescriptionWidget, DefineColorsWidget,
                      SliderSelectMultipleColors, SliderSelectMultipleDescriptors, SliderRadioSelectDescriptor,
                      SliderRadioSelectColor, SliderSelectMultipleNumbers, SliderRadioSelectNumber,
                      SliderRadioSelectTaxonfilter, SliderSelectMultipleTaxonfilters,
                      SliderSelectMultipleTextDescriptors, SliderRadioSelectTextDescriptor,
                      DefineTextDescriptionWidget)

from decimal import Decimal

from base64 import b64encode

import json

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
    
    MatrixSingleChoiceWidget = forms.Select
    MatrixMultipleChoiceWidget = forms.CheckboxSelectMultiple


    # a form field for defining a valid space for a node
    NodeSpaceDefinitionFormFieldClass = None
    NodeSpaceDefinitionFormFieldWidget = None

    # e.g. color for ColorFilter
    verbose_space_name = None

    # these will be saved in the db automatically
    definition_parameters = []

    # filters are instantiated by passing in a MatrixFilter model instance: matrix_filter
    def __init__(self, matrix_filter):

        self.matrix_filter = matrix_filter

        # set encoded_space for the matrix_filter
        self.set_encoded_space(matrix_filter)

        # check if the user allows the end-user to select multiple values 
        allow_multiple_values = False
        if self.matrix_filter.definition:
            allow_multiple_values = self.matrix_filter.definition.get('allow_multiple_values', False)

        if allow_multiple_values:
            self.MatrixFormFieldClass = self.MatrixMultipleChoiceFormFieldClass
            self.MatrixFormFieldWidget = self.MatrixMultipleChoiceWidget

        else:
            self.MatrixFormFieldClass = self.MatrixSingleChoiceFormFieldClass
            self.MatrixFormFieldWidget = self.MatrixSingleChoiceWidget

    ### DEFINITION
    def get_default_definition(self):
        return {}

    # make sure the definition is complete
    def set_definition(self, matrix_filter):

        if not matrix_filter.definition:
            default_definition = self.get_default_definition()
            matrix_filter.definition = default_definition

    ### ENCODED SPACE
    def get_empty_encoded_space(self):
        raise NotImplementedError('MatrixFilterType subclasses need a get_empty_encoded_space method')

    # make sure there is at least the empty space
    def set_encoded_space(self, matrix_filter):
        raise NotImplementedError('MatrixFilterType subclasses need a set_encoded_space method')

    ### FORM FIELDS
    # the field displayed when end-user uses the identification matrix
    def get_matrix_form_field(self):
        raise NotImplementedError('MatrixFilterType subclasses need a get_matrix_form_field method')

    def get_matrix_form_field_widget(self):
        extra_context = {
            'matrix_filter_space_ctype' : ContentType.objects.get_for_model(self.matrix_filter.space_model)
        }
        widget = self.MatrixFormFieldWidget(self.matrix_filter, extra_context=extra_context)
        return widget

    # the field when adding/editing a matrix node
    # display a field with min value, max value and units
    def get_node_space_field_kwargs(self):
        return {}

    def get_node_space_widget_attrs(self):
        return {}
    
    def get_node_space_definition_form_field(self, from_url):
        widget_attrs = self.get_node_space_widget_attrs()
        field_kwargs = self.get_node_space_field_kwargs()
        

        field = self.NodeSpaceDefinitionFormFieldClass(
            widget=self.NodeSpaceDefinitionFormFieldWidget(attrs=widget_attrs), **field_kwargs)

        return field

    # in the ChildrenJsonCache, the (child)node's matrix filter values are stored as a list of values
    # receives a NodeFilterSpace instance
    def get_node_filter_space_as_list(self, node_filter_space):
        raise NotImplementedError('MatrixFilterType subclasses need a get_node_filter_space_as_list')
    
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

    def set_encoded_space(self, matrix_filter):
        matrix_filter_space = matrix_filter.get_space().first()

        if matrix_filter_space:
            matrix_filter.encoded_space = matrix_filter_space.encoded_space
        else:
            matrix_filter.encoded_space = self.get_empty_encoded_space()


class MultiSpaceFilterMixin:

    def encode_entity_form_value(self, form_value):
        raise NotImplementedError('%s is a multispatial filter and cant encode single form values' % self.__class__.__name__)


    def get_empty_encoded_space(self):
        return []

    def set_encoded_space(self, matrix_filter):
        
        matrix_filter.encoded_space = self.get_empty_encoded_space()
        
        matrix_filter_spaces = matrix_filter.get_space()

        if matrix_filter_spaces:
            encoded_space = []
            for space in matrix_filter_spaces:
                matrix_filter.encoded_space.append(space.encoded_space)
        

'''
    RangeFilter
    - encoded: [0,10]
'''
class RangeFilter(SingleSpaceFilterMixin, MatrixFilterType):

    verbose_name = _('Range filter')
    definition_parameters = ['step', 'unit', 'unit_verbose']

    MatrixSingleChoiceFormFieldClass = forms.DecimalField
    MatrixMultipleChoiceFormFieldClass = forms.DecimalField

    MatrixSingleChoiceWidget = RangePropertyWidget
    MatrixMultipleChoiceWidget = RangePropertyWidget

    NodeSpaceDefinitionFormFieldClass = RangeSpaceField
    NodeSpaceDefinitionFormFieldWidget = DefineRangeSpaceWidget

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
    def get_matrix_form_field(self):
        # decimalfield as a slider
        widget = self.get_matrix_form_field_widget()
        
        return self.MatrixFormFieldClass(required=False, label=self.matrix_filter.name,
                    min_value=self.matrix_filter.encoded_space[0], max_value=self.matrix_filter.encoded_space[1],
                    decimal_places=None, widget=widget)


    # display a field with min value, max value and units
    def get_node_space_field_kwargs(self):
        field_kwargs = {
            'subfield_kwargs': {
                'decimal_places' : None,
            }
        }
        return field_kwargs

    def get_node_space_widget_attrs(self):

        if self.matrix_filter.definition:
            unit = self.matrix_filter.definition.get('unit', '')
            step =  self.matrix_filter.definition.get('step', 1)
        else:
            unit = ''
            step = 1
            
        widget_attrs = {
            'extra_context': {
                'unit' : unit,
            },
            'step' : step,
        }
        return widget_attrs

    # ENCODE FORM VALUES TO ENCODED SPACES
    # A
    def get_encoded_space_from_form(self, form):
        encoded_space = [form.cleaned_data['min_value'], form.cleaned_data['max_value']]
        return encoded_space

    # the form field already produces [min,max]
    def encode_entity_form_value(self, form_value):
        return form_value

    # FILL FORMS
    # get initial for form
    def get_space_initial(self):
        space_initial = {
            'min_value' : self.matrix_filter.encoded_space[0],
            'max_value' : self.matrix_filter.encoded_space[1]
        }
        return space_initial


    # node filter space as list
    def get_node_filter_space_as_list(self, node_filter_space):
        # range filter stores [min,max] as encoded space
        return node_filter_space.encoded_space


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

    definition_parameters = ['unit', 'unit_verbose']
    
    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixMultipleChoiceWidget = SliderSelectMultipleNumbers
    MatrixSingleChoiceWidget = SliderRadioSelectNumber
    
    NodeSpaceDefinitionFormFieldClass = forms.MultipleChoiceField
    NodeSpaceDefinitionFormFieldWidget = forms.CheckboxSelectMultiple

    def get_default_definition(self):
        definition = {
            unit : '',
        }

        return definition

    def get_empty_encoded_space(self):
        return []            

    def _strip(self, number_str):
        return number_str.rstrip('0').rstrip('.')

    def _get_choices(self):
        
        choices = []
        for number in self.matrix_filter.encoded_space:
            choices.append((self._strip(str(number)), self._strip(str(number))))

        return choices

    # FORM FIELDS
    def get_matrix_form_field(self):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget()
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)

    def get_node_space_field_kwargs(self):
        kwargs = {
            'choices' : self._get_choices(),
        }
        return kwargs

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


    # node filter space as list
    def get_node_filter_space_as_list(self, node_filter_space):
        # number filter stores [x,y,z] as encoded space
        return node_filter_space.encoded_space


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


'''
    ColorFilter
    - one MatrixFilterSpace entry for one color - this enables editing one single color
    - encoded_space [r,g,b,a]
'''
class ColorFilter(MultiSpaceFilterMixin, MatrixFilterType):

    is_multispace = True

    definition_parameters = []

    verbose_name = _('Color filter')
    verbose_space_name = _('color')

    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixSingleChoiceWidget = SliderRadioSelectColor
    MatrixMultipleChoiceWidget = SliderSelectMultipleColors
    
    NodeSpaceDefinitionFormFieldClass = forms.MultipleChoiceField
    NodeSpaceDefinitionFormFieldWidget = DefineColorsWidget   


    # COLOR ENCODING CONVERSION
    # transform hex values #RRGGBB or #RRGGBBAA to the encoded form [r,g,b,a]
    def encode_from_hex(self, value):
        """Return (red, green, blue) for the color given as #rrggbbaa or rrggbb."""
        value = value.lstrip('#')

        if len(value) == 6:
            lv = len(value)
            encoded_color = [int(value[i:i+2], 16) for i in (0, 2 ,4)] + [1]
        elif len(value) == 8:
            encoded_color = [int(value[i:i+2], 16) for i in (0, 2 ,4)] + [round(float(int(value[6:8],16)/255),2)]
        else:
            raise ValueError('hex color has to be in the format #RRGGBB or #RRGGBBAA')

        return encoded_color


    def encoded_space_to_hex(self, encoded_space):
        return self.rgb_to_hex(encoded_space[0], encoded_space[1], encoded_space[2], encoded_space[3])
        

    def rgb_to_hex(self, r, g, b, a=None):
        """Return color as #rrggbb for the given color values."""
        if a is not None:
            return '#%02x%02x%02x%02x' % (r, g, b, a)
        return '#%02x%02x%02x' % (r, g, b)

    def encoded_space_to_rgba_str(self, encoded_space):

        r = encoded_space[0]
        g = encoded_space[1]
        b = encoded_space[2]
        a = 1
        
        if len(encoded_space) >= 4:
            a = encoded_space[3]
        
        rgba_str = 'rgba({0},{1},{2},{3})'.format(r,g,b,a)

        return rgba_str

    def decode(self, encoded_space):
        return self.encoded_space_to_rgba_str(encoded_space)

    def _get_choices(self):

        choices = []

        for space in self.matrix_filter.get_space():
            encoded_space = space.encoded_space
            #r,g,b,a
            choice_value = ','.join(str(n) for n in encoded_space)
            color_rgba = self.encoded_space_to_rgba_str(encoded_space)

            extra_kwargs = {
                'modify' : True,
                'space_id' : space.id,
            }

            choice = (choice_value, color_rgba, extra_kwargs)
            
            choices.append(choice)

        return choices

    def get_matrix_form_field(self):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget()
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)

    def get_node_space_definition_form_field(self, from_url):
        queryset = self.matrix_filter.get_space()
        extra_context = {
            'from_url' : from_url,
        }
        return ObjectLabelModelMultipleChoiceField(queryset, widget=DefineColorsWidget(self,
                                                                                       extra_context=extra_context))

    # READ FORMS
    # ColorFilter is multispatial
    def get_encoded_space_from_form(self, form):
        return []

    # FILL FORMS
    # ColorFilter is multispace, spaces are added using a separate form
    def get_space_initial(self):
        return {}

    def get_single_space_initial(self, matrix_filter_space):

        color_hex = self.encoded_space_to_hex(matrix_filter_space.encoded_space)

        # currently, the html color input does not support alpha channels, respect leading #
        if len(color_hex) > 7:
            color_hex = color_hex[:7]
        
        initial = {
            'color' : color_hex,
        }
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

        # put the color into the encoded space
        hex_value = form.cleaned_data['color']
        encoded_space = self.encode_from_hex(hex_value)

        space.encoded_space = encoded_space
        space.save(old_encoded_space=old_encoded_space)

        return space


    # node filter space as list
    def get_node_filter_space_as_list(self, node_filter_space):
        # return a list of 4-tuples
        space_list = []

        for node_space in node_filter_space.values.all():
            space_list.append(node_space.encoded_space)
            
        return space_list


    def validate_encoded_space(self, space):
        
        is_valid = True
        
        #[r,g,b,a]
        if isinstance(space, list) and len(space) == 4:
            r = space[0]
            g = space[1]
            b = space[2]
            a = space[3]

            for parameter in [r,g,b]:
                if not isinstance(parameter, int):
                    is_valid = False
                    break

            if isinstance(a, float) or isinstance(a, int):
                pass
            else:
                is_valid = True
                    
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

    definition_parameters = []

    verbose_name = _('Text/Images filter')
    verbose_space_name = _('text with image')
    
    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixMultipleChoiceWidget = SliderSelectMultipleDescriptors
    MatrixSingleChoiceWidget = SliderRadioSelectDescriptor
    
    NodeDefinitionFormFieldClass = ObjectLabelModelMultipleChoiceField
    NodeDefinitionFormFieldWidget = DefineDescriptionWidget

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
            }

            image = space.image()
            if image and image.image_store.source_image:
                extra_kwargs['image'] = image
            
            choices.append((space.encoded_space, space.encoded_space, extra_kwargs))

        return choices

    def get_matrix_form_field(self):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget()
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)

    '''
    this method needs a queryset in the space as it works with ModelMultipleChoiceField
    '''
    def get_node_space_definition_form_field(self, from_url):
        queryset = self.matrix_filter.get_space()
        extra_context = {
            'from_url' : from_url,
        }
        return ObjectLabelModelMultipleChoiceField(queryset, widget=DefineDescriptionWidget(self,
                                                                            extra_context=extra_context))


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
    def get_node_filter_space_as_list(self, node_filter_space):
        space_list = []
        for space in node_filter_space.values.all():
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

    definition_parameters = []

    verbose_name = _('Text only filter')
    verbose_space_name = _('text')
    
    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixMultipleChoiceWidget = SliderSelectMultipleTextDescriptors
    MatrixSingleChoiceWidget = SliderRadioSelectTextDescriptor
    
    NodeDefinitionFormFieldClass = ObjectLabelModelMultipleChoiceField
    NodeDefinitionFormFieldWidget = DefineDescriptionWidget


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

    def get_matrix_form_field(self):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget()
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)


    # in the ChildrenJsonCache, the (child)node's matrix filter values are stored as a list of values
    # receives a NodeFilterSpace instance
    def get_node_filter_space_as_list(self, node_filter_space):
        space_list = []
        for space in node_filter_space.values.all():
            space_list.append(space.encoded_space)
        return space_list
    
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


    def get_node_space_definition_form_field(self, from_url):
        queryset = self.matrix_filter.get_space()
        extra_context = {
            'from_url' : from_url,
        }
        return ObjectLabelModelMultipleChoiceField(queryset, widget=DefineTextDescriptionWidget(self,
                                                                            extra_context=extra_context))

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

    definition_parameters = []

    verbose_name = _('Taxonomic Filter')
    verbose_space_name = _('Taxon')
    
    MatrixSingleChoiceFormFieldClass = forms.ChoiceField
    MatrixMultipleChoiceFormFieldClass = forms.MultipleChoiceField

    MatrixSingleChoiceWidget = SliderRadioSelectTaxonfilter
    MatrixMultipleChoiceWidget = SliderSelectMultipleTaxonfilters
    
    NodeDefinitionFormFieldClass = ObjectLabelModelMultipleChoiceField
    NodeDefinitionFormFieldWidget = DefineDescriptionWidget

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
                # "taxon_source": "taxonomy.sources.col", "taxon_latname": "Animalia"}],"latname": "Animalia",
                # "is_custom": false}

                taxonfilter_json = json.dumps(taxonfilter)
                
                extra_kwargs = {
                    'image' : static('app_kit/buttons/taxonfilters/%s.svg' %(taxonfilter['latname']) ),
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
    

    def get_matrix_form_field(self):
        choices = self._get_choices()
        widget = self.get_matrix_form_field_widget()
        return self.MatrixFormFieldClass(label=self.matrix_filter.name, widget=widget,
                                         choices=choices, required=False)

    # READ FORMS

    def make_taxonfilter_taxon(self, lazy_taxon):
        taxonfilter_entry = {
            'taxon_source' : lazy_taxon.taxon_source,
            'taxon_latname' : lazy_taxon.taxon_latname,
            'taxon_author' : lazy_taxon.taxon_author,
            'name_uuid' : lazy_taxon.name_uuid,
            'taxon_nuid' : lazy_taxon.taxon_nuid,
        }

        return taxonfilter_entry

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

    def get_node_space_definition_form_field(self, from_url):
        return None


    def get_node_filter_space_as_list(self, node_filter_space):
        raise NotImplementedError('TaxonFilter does not support encoded_space')

    # taxon json
    #{"taxa": [{"taxon_nuid": "001", "name_uuid": "f61b30e9-90d3-4e87-9641-eee71506aada",
    # "taxon_source": "taxonomy.sources.col", "taxon_latname": "Animalia"}],"latname": "Animalia",
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

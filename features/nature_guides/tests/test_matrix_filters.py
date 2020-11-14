from django_tenants.test.cases import TenantTestCase
from django import forms

from app_kit.tests.common import test_settings

from app_kit.features.nature_guides.models import (NatureGuide, MetaNode, NatureGuidesTaxonTree, MatrixFilter,
                                                   MatrixFilterSpace, NodeFilterSpace)

from app_kit.features.nature_guides.matrix_filters import (MatrixFilterType, SingleSpaceFilterMixin,
                            MultiSpaceFilterMixin, RangeFilter, NumberFilter, ColorFilter,
                            DescriptiveTextAndImagesFilter, TextOnlyFilter, TaxonFilter)

from app_kit.features.nature_guides.fields import RangeSpaceField, ObjectLabelModelMultipleChoiceField

from app_kit.features.nature_guides.widgets import (RangePropertyWidget, DefineRangeSpaceWidget,
                    DefineDescriptionWidget, DefineColorsWidget, SliderSelectMultipleColors,
                    SliderSelectMultipleDescriptors, SliderRadioSelectDescriptor, SliderRadioSelectColor,
                    SliderSelectMultipleNumbers, SliderRadioSelectNumber, SliderRadioSelectTaxonfilter,
                    SliderSelectMultipleTaxonfilters, SliderSelectMultipleTextDescriptors,
                    SliderRadioSelectTextDescriptor, DefineTextDescriptionWidget)

from app_kit.features.nature_guides.matrix_filter_forms import (RangeFilterManagementForm,
                    NumberFilterManagementForm, ColorFilterManagementForm, TaxonFilterManagementForm)

from app_kit.features.nature_guides.matrix_filter_space_forms import (ColorFilterSpaceForm,
                    DescriptiveTextAndImagesFilterSpaceForm, TextOnlyFilterSpaceForm)

from app_kit.features.nature_guides.tests.common import WithNatureGuide, WithMatrixFilters

from app_kit.tests.mixins import WithMetaApp

from taxonomy.lazy import LazyTaxonList, LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from base64 import b64encode, b64decode
from django.templatetags.static import static

import json


class MatrixFilterTestCommon:

    MatrixFilterTypeClass = None

    def setUp(self):
        super().setUp()
        self.nature_guide = self.create_nature_guide()

        self.root_node = NatureGuidesTaxonTree.objects.get(nature_guide=self.nature_guide,
                                                           meta_node__node_type='root')

        self.root_meta_node = self.root_node.meta_node


    @test_settings
    def test_get_default_definition(self):

        definition = self.matrix_filter.matrix_filter_type.get_default_definition()
        self.assertEqual(definition, {})        


    @test_settings
    def test_get_matrix_form_field_widget(self):

        widget = self.matrix_filter.matrix_filter_type.get_matrix_form_field_widget()
        self.assertTrue(isinstance(widget, self.matrix_filter.matrix_filter_type.MatrixFormFieldWidget))


    @test_settings
    def test_get_node_space_field_kwargs(self):
        field_kwargs = self.matrix_filter.matrix_filter_type.get_node_space_field_kwargs()
        self.assertEqual(field_kwargs, {})
        

    @test_settings
    def test_get_node_space_widget_attrs(self):
        widget_attrs = self.matrix_filter.matrix_filter_type.get_node_space_widget_attrs()
        self.assertEqual(widget_attrs, {})


    @test_settings
    def test_get_node_space_definition_form_field(self):
        from_url = '/test-url/'
        field = self.matrix_filter.matrix_filter_type.get_node_space_definition_form_field(from_url)

        self.assertTrue(isinstance(field,
                                   self.matrix_filter.matrix_filter_type.NodeSpaceDefinitionFormFieldClass))

        
class TestRangeFilter(MatrixFilterTestCommon, WithNatureGuide, WithMatrixFilters, TenantTestCase):

    def setUp(self):
        super().setUp()

        filter_kwargs = {
            'definition' : {
                'step' : 1,
                'unit' : 'cm',
                'unit_verbose' : 'centimeters',
            }
        }

        self.matrix_filter = self.create_matrix_filter('Range Filter', self.root_meta_node, 'RangeFilter',
                                                       **filter_kwargs)

        self.encoded_space = [-4,4]


    def create_space(self):
        
        self.matrix_filter_space = MatrixFilterSpace(
            matrix_filter = self.matrix_filter,
            encoded_space = self.encoded_space,
        )

        self.matrix_filter_space.save()

    def check_field_classes(self, range_filter):

        self.assertEqual(range_filter.MatrixSingleChoiceFormFieldClass, forms.DecimalField)
        self.assertEqual(range_filter.MatrixMultipleChoiceFormFieldClass, forms.DecimalField)

        self.assertEqual(range_filter.MatrixSingleChoiceWidgetClass, RangePropertyWidget)
        self.assertEqual(range_filter.MatrixMultipleChoiceWidgetClass, RangePropertyWidget)

        self.assertEqual(range_filter.NodeSpaceDefinitionFormFieldClass, RangeSpaceField)
        self.assertEqual(range_filter.NodeSpaceDefinitionWidgetClass, DefineRangeSpaceWidget)

        self.assertEqual(range_filter.matrix_filter, self.matrix_filter)

        self.assertEqual(range_filter.MatrixFormFieldClass, forms.DecimalField)
        self.assertEqual(range_filter.MatrixFormFieldWidget, RangePropertyWidget)


    @test_settings
    def test_init_no_encoded_space(self):

        range_filter = RangeFilter(self.matrix_filter)

        self.assertFalse(range_filter.is_multispace)
        
        self.check_field_classes(range_filter)

        # no encoded space, so set_encoded_space
        expected_space = [0,0]
        self.assertEqual(range_filter.matrix_filter.encoded_space, expected_space)


    @test_settings
    def test_init_with_encoded_space(self):

        self.create_space()

        range_filter = RangeFilter(self.matrix_filter)
        
        self.check_field_classes(range_filter)

        # no encoded space, so set_encoded_space
        self.assertEqual(range_filter.matrix_filter.encoded_space, self.encoded_space)


    @test_settings
    def test_get_empty_encoded_space(self):

        range_filter = RangeFilter(self.matrix_filter)

        empty_space = range_filter.get_empty_encoded_space()
        self.assertEqual(empty_space, [0,0])


    @test_settings
    def test_set_encoded_space(self):

        range_filter = RangeFilter(self.matrix_filter)
        empty_space = range_filter.get_empty_encoded_space()

        range_filter.set_encoded_space()
        self.assertEqual(self.matrix_filter.encoded_space, empty_space)

        self.create_space()
        range_filter.set_encoded_space()
        self.assertEqual(self.matrix_filter.encoded_space, self.encoded_space)


    @test_settings
    def test_get_matrix_form_field(self):

        self.create_space()
        
        range_filter = RangeFilter(self.matrix_filter)
        
        field = range_filter.get_matrix_form_field()

        self.assertTrue(isinstance(field, forms.DecimalField))
        self.assertFalse(field.required)
        self.assertEqual(field.min_value, -4)
        self.assertEqual(field.max_value, 4)


    @test_settings
    def test_get_node_space_field_kwargs(self):

        range_filter = RangeFilter(self.matrix_filter)
        kwargs = range_filter.get_node_space_field_kwargs()
        self.assertEqual(kwargs['subfield_kwargs']['decimal_places'], None)


    @test_settings
    def test_get_node_space_widget_attrs(self):

        # first, test without definition
        self.matrix_filter.definition = None
        self.matrix_filter.save()
        range_filter = RangeFilter(self.matrix_filter)

        widget_attrs = range_filter.get_node_space_widget_attrs()

        expected_attrs = {
            'step' : 1,
            'extra_context' : {
                'unit' : '',
            }
        }
        self.assertEqual(widget_attrs, expected_attrs)

        # second, test with definition
        definition = {
            'step' : 0.5,
            'unit' : 'cm',
        }

        self.matrix_filter.definition = definition
        self.matrix_filter.save()
        self.matrix_filter.refresh_from_db()

        range_filter = RangeFilter(self.matrix_filter)

        widget_attrs = range_filter.get_node_space_widget_attrs()

        expected_attrs = {
            'step' : 0.5,
            'extra_context' : {
                'unit' : 'cm',
            }
        }
        self.assertEqual(widget_attrs, expected_attrs)


    @test_settings
    def test_get_encoded_space_from_form(self):

        data = {
            'name' : 'Range Filter',
            'filter_type' : 'RangeFilter',
            'input_language' : 'en',
            'min_value' : '-10',
            'max_value' : '10.5',
            'step' : '0.5',
        }

        form = RangeFilterManagementForm(self.root_meta_node, self.root_node, data=data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        range_filter = RangeFilter(self.matrix_filter)
        
        encoded_space = range_filter.get_encoded_space_from_form(form)
        self.assertEqual(encoded_space, [-10,10.5])


    @test_settings
    def test_encode_entity_form_value(self):

        range_filter = RangeFilter(self.matrix_filter)
        form_value = range_filter.encode_entity_form_value([-4,4])


    @test_settings
    def test_get_space_initial(self):

        range_filter = RangeFilter(self.matrix_filter)
        initial = range_filter.get_space_initial()
        expected_initial = {
            'min_value' : 0,
            'max_value' : 0,
        }
        self.assertEqual(initial, expected_initial)

        # test with space
        self.create_space()
        self.matrix_filter.refresh_from_db()
        range_filter = RangeFilter(self.matrix_filter)
        initial = range_filter.get_space_initial()
        expected_initial = {
            'min_value' : -4,
            'max_value' : 4,
        }

        self.assertEqual(initial, expected_initial)


    @test_settings
    def test_get_node_filter_space_as_list(self):
        self.create_space()

        child = self.create_node(self.root_node, 'Child')
        
        node_filter_space = NodeFilterSpace(
            node=child,
            matrix_filter = self.matrix_filter,
            encoded_space = [-2,2],
        )

        node_filter_space.save()

        range_filter = RangeFilter(self.matrix_filter)
        space_list = range_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, [-2,2])
        

    @test_settings
    def test_validate_encoded_space(self):

        range_filter = RangeFilter(self.matrix_filter)

        error_spaces = ['a', [1,2,3],[],[1]]

        for space in error_spaces:

            is_valid = range_filter.validate_encoded_space(space)
            self.assertFalse(is_valid)

        good_space = [-1,1]

        is_valid = range_filter.validate_encoded_space(good_space)
        self.assertTrue(is_valid)
            

    @test_settings
    def test_get_default_definition(self):
        range_filter = RangeFilter(self.matrix_filter)

        definition = range_filter.get_default_definition()
        expected_definition = {
            'step' : 1,
            'unit' : '',
            'unit_verbose' : '',
        }

        self.assertEqual(definition, expected_definition)
        

class TestNumberFilter(MatrixFilterTestCommon, WithNatureGuide, WithMatrixFilters, TenantTestCase):

    def setUp(self):
        super().setUp()

        filter_kwargs = {
            'definition' : {
                'unit' : 'cm',
                'unit_verbose' : 'centimeters',
            }
        }

        self.matrix_filter = self.create_matrix_filter('Number Filter', self.root_meta_node, 'NumberFilter',
                                                       **filter_kwargs)

        self.encoded_space = [1,3,5.5,10]


    def create_space(self):
        
        self.matrix_filter_space = MatrixFilterSpace(
            matrix_filter = self.matrix_filter,
            encoded_space = self.encoded_space,
        )

        self.matrix_filter_space.save()


    def check_field_classes(self, number_filter):

        self.assertEqual(number_filter.MatrixSingleChoiceFormFieldClass, forms.ChoiceField)
        self.assertEqual(number_filter.MatrixMultipleChoiceFormFieldClass, forms.MultipleChoiceField)

        self.assertEqual(number_filter.MatrixSingleChoiceWidgetClass, SliderRadioSelectNumber)
        self.assertEqual(number_filter.MatrixMultipleChoiceWidgetClass, SliderSelectMultipleNumbers)

        self.assertEqual(number_filter.NodeSpaceDefinitionFormFieldClass, forms.MultipleChoiceField)
        self.assertEqual(number_filter.NodeSpaceDefinitionWidgetClass, forms.CheckboxSelectMultiple)

        self.assertEqual(number_filter.matrix_filter, self.matrix_filter)

        self.assertEqual(number_filter.MatrixFormFieldClass, forms.ChoiceField)
        self.assertEqual(number_filter.MatrixFormFieldWidget, SliderRadioSelectNumber)


    @test_settings
    def test_init_no_encoded_space(self):

        number_filter = NumberFilter(self.matrix_filter)

        self.assertFalse(number_filter.is_multispace)
        
        self.check_field_classes(number_filter)

        # no encoded space, so set_encoded_space
        expected_space = []
        self.assertEqual(number_filter.matrix_filter.encoded_space, expected_space)


    @test_settings
    def test_init_with_encoded_space(self):

        self.create_space()

        number_filter = NumberFilter(self.matrix_filter)

        self.assertFalse(number_filter.is_multispace)
        
        self.check_field_classes(number_filter)

        # no encoded space, so set_encoded_space
        expected_space = self.encoded_space
        self.assertEqual(number_filter.matrix_filter.encoded_space, expected_space)


    @test_settings
    def test_get_default_definition(self):

        number_filter = NumberFilter(self.matrix_filter)

        default_definition = number_filter.get_default_definition()

        expected_definition = {
            'unit' : ''
        }

        self.assertEqual(default_definition, expected_definition)
        

    @test_settings
    def test_get_empty_encoded_space(self):

        number_filter = NumberFilter(self.matrix_filter)

        empty_space = number_filter.get_empty_encoded_space()
        self.assertEqual(empty_space, [])


    @test_settings
    def test_strip(self):

        number_filter = NumberFilter(self.matrix_filter)

        number = '1200.0000'

        number_clean = number_filter._strip(number)
        self.assertEqual(number_clean, '1200')

        number_2 = '1200'

        number_2_clean = number_filter._strip(number_2)
        self.assertEqual(number_2_clean, '1200')


    @test_settings
    def test_get_choices(self):

        number_filter = NumberFilter(self.matrix_filter)
        
        choices = number_filter._get_choices()

        self.assertEqual(choices, [])

        # test with space
        self.create_space()
        self.matrix_filter.refresh_from_db()
        number_filter = NumberFilter(self.matrix_filter)
        choices = number_filter._get_choices()
        self.assertEqual(choices, [('1', '1'),('3', '3'),('5.5','5.5'),('10','10')])


    @test_settings
    def test_get_matrix_form_field(self):

        number_filter = NumberFilter(self.matrix_filter)

        field = number_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertFalse(field.required)
        self.assertEqual(field.choices, [])

        # test with space
        self.create_space()
        self.matrix_filter.refresh_from_db()
        number_filter = NumberFilter(self.matrix_filter)
        field = number_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertFalse(field.required)
        self.assertEqual(field.choices, [('1', '1'),('3', '3'),('5.5','5.5'),('10','10')])

    @test_settings
    def test_get_node_space_field_kwargs(self):

        self.create_space()
        number_filter = NumberFilter(self.matrix_filter)

        kwargs = number_filter.get_node_space_field_kwargs()

        expected_kwargs = {
            'choices' : [('1', '1'),('3', '3'),('5.5','5.5'),('10','10')],
        }

        self.assertEqual(kwargs, expected_kwargs)


    @test_settings
    def test_get_encoded_space_from_form(self):

        data = {
            'name' : 'Number Filter',
            'filter_type' : 'NumberFilter',
            'input_language' : 'en',
            'numbers' : '2,5,1,10,1.010',
        }

        form = NumberFilterManagementForm(self.root_meta_node, self.root_node, data=data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        number_filter = NumberFilter(self.matrix_filter)
        
        encoded_space = number_filter.get_encoded_space_from_form(form)
        self.assertEqual(encoded_space, [1.0, 1.01,2.0,5.0,10.0])
        

    @test_settings
    def test_encode_entity_form_value(self):

        form_value = ['1','-1','0','5.5']
        number_filter = NumberFilter(self.matrix_filter)

        value = number_filter.encode_entity_form_value(form_value)
        self.assertEqual(value, [-1.0,0.0,1.0,5.5])
    

    @test_settings
    def test_get_space_initial(self):

        self.create_space()

        number_filter = NumberFilter(self.matrix_filter)
        initial = number_filter.get_space_initial()

        expected_initial = {
            'numbers' : '1,3,5.5,10',
        }

        self.assertEqual(initial, expected_initial)
    

    @test_settings
    def test_get_node_filter_space_as_list(self):

        self.create_space()

        child = self.create_node(self.root_node, 'Child')
        
        node_filter_space = NodeFilterSpace(
            node=child,
            matrix_filter = self.matrix_filter,
            encoded_space = [1,3],
        )

        node_filter_space.save()

        number_filter = NumberFilter(self.matrix_filter)
        space_list = number_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, [1,3])
        

    @test_settings
    def test_set_encoded_space(self):
        # no space
        number_filter = NumberFilter(self.matrix_filter)

        number_filter.set_encoded_space()
        self.assertEqual(self.matrix_filter.encoded_space, [])
        
        # with space
        self.create_space()
        self.matrix_filter.refresh_from_db()
        number_filter = NumberFilter(self.matrix_filter)
        number_filter.set_encoded_space()

        self.assertEqual(self.matrix_filter.encoded_space, self.encoded_space)
        

    @test_settings
    def test_validate_encoded_space(self):

        number_filter = NumberFilter(self.matrix_filter)

        invalid_spaces = ['a', 1, ['a',1,2,3]]

        for space in invalid_spaces:
            is_valid = number_filter.validate_encoded_space(space)
            self.assertFalse(is_valid)

        valid_space = [1,2,1.1,10]

        is_valid = number_filter.validate_encoded_space(valid_space)
        self.assertTrue(is_valid)



# respect both single colors and gradient
class TestColorFilter(MatrixFilterTestCommon, WithNatureGuide, WithMatrixFilters, TenantTestCase):

    def setUp(self):
        super().setUp()

        filter_kwargs = {
            'definition' : {
                'allow_multiple_values' : False,
            }
        }

        self.matrix_filter = self.create_matrix_filter('Color Filter', self.root_meta_node, 'ColorFilter',
                                                       **filter_kwargs)

    def create_space(self, color_list):
        
        matrix_filter_space = MatrixFilterSpace(
            matrix_filter = self.matrix_filter,
            encoded_space = color_list,
        )

        if isinstance(color_list[0], list):
            matrix_filter_space.additional_information = {
                'gradient' : True,
            }

        matrix_filter_space.save()

        return matrix_filter_space


    def check_field_classes(self, color_filter):

        self.assertEqual(color_filter.MatrixSingleChoiceFormFieldClass, forms.ChoiceField)
        self.assertEqual(color_filter.MatrixMultipleChoiceFormFieldClass, forms.MultipleChoiceField)

        self.assertEqual(color_filter.MatrixSingleChoiceWidgetClass, SliderRadioSelectColor)
        self.assertEqual(color_filter.MatrixMultipleChoiceWidgetClass, SliderSelectMultipleColors)

        self.assertEqual(color_filter.NodeSpaceDefinitionFormFieldClass, ObjectLabelModelMultipleChoiceField)
        self.assertEqual(color_filter.NodeSpaceDefinitionWidgetClass, DefineColorsWidget)

        self.assertEqual(color_filter.matrix_filter, self.matrix_filter)


        if self.matrix_filter.definition and self.matrix_filter.definition.get('allow_multiple_values', False) == False:
            self.assertEqual(color_filter.MatrixFormFieldClass, forms.ChoiceField)
            self.assertEqual(color_filter.MatrixFormFieldWidget, SliderRadioSelectColor)

        else:
            self.assertEqual(color_filter.MatrixFormFieldClass, forms.MultipleChoiceField)
            self.assertEqual(color_filter.MatrixFormFieldWidget, SliderSelectMultipleColors)


    # test both single space and multispace
    @test_settings
    def test_init_no_encoded_space(self):

        color_filter = ColorFilter(self.matrix_filter)

        self.assertTrue(color_filter.is_multispace)
        
        self.check_field_classes(color_filter)

        # no encoded space, so set_encoded_space
        expected_space = []
        self.assertEqual(color_filter.matrix_filter.encoded_space, expected_space)


    @test_settings
    def test_init_with_encoded_space(self):
        space_1 = self.create_space([111,222,255,1])
        space_2 = self.create_space([255,222,111,1])

        color_filter = ColorFilter(self.matrix_filter)

        expected_space = [[111,222,255,1],[255,222,111,1]]
        self.assertEqual(color_filter.matrix_filter.encoded_space, expected_space)

        # test multiple values
        self.matrix_filter.definition = {
            'allow_multiple_values' : True,
        }

        self.matrix_filter.save()

        color_filter = ColorFilter(self.matrix_filter)
        self.assertTrue(self.matrix_filter.definition.get('allow_multiple_values',False))

        self.check_field_classes(color_filter)


    @test_settings
    def test_set_encoded_space(self):

        # empty
        color_filter = ColorFilter(self.matrix_filter)
        color_filter.set_encoded_space()
        self.assertEqual(color_filter.matrix_filter.encoded_space, [])

        space_1 = self.create_space([111,222,255,1])
        space_2 = self.create_space([255,222,111,1])

        # multple spaces
        color_filter.set_encoded_space()
        expected_space = [[111,222,255,1],[255,222,111,1]]
        self.assertEqual(color_filter.matrix_filter.encoded_space, expected_space)

        # one gradient
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_3 = self.create_space(gradient)

        color_filter.set_encoded_space()
        expected_space_w_gradient = [[111,222,255,1],[255,222,111,1], [[0,0,0,1],[255,255,255,1]]]
        self.assertEqual(color_filter.matrix_filter.encoded_space, expected_space_w_gradient)
        
        
    @test_settings
    def test_get_empty_encoded_space(self):

        color_filter = ColorFilter(self.matrix_filter)
        empty_space = color_filter.get_empty_encoded_space()
        self.assertEqual(empty_space, [])
    

    @test_settings
    def test_encode_from_hex(self):
        color_filter = ColorFilter(self.matrix_filter)
        
        rgb = '#ffffff'
        encoded_white = color_filter.encode_from_hex(rgb)
        expected_white = [255,255,255,1]
        self.assertEqual(encoded_white, expected_white)

        rgba = '#000000ff'
        encoded_black = color_filter.encode_from_hex(rgba)
        expected_black = [0,0,0,1]
        self.assertEqual(encoded_black, expected_black)
        

    @test_settings
    def test_encoded_space_to_hex(self):

        color_filter = ColorFilter(self.matrix_filter)

        encoded_white_alpha = [255,255,255,1]
        expected_hex_white_alpha= '#ffffffff'
        hex_white_alpha = color_filter.encoded_space_to_hex(encoded_white_alpha)

        self.assertEqual(expected_hex_white_alpha, hex_white_alpha)

        encoded_black = [0,0,0,1]
        expected_hex_black = '#000000ff'
        hex_black = color_filter.encoded_space_to_hex(encoded_black)
        
        self.assertEqual(hex_black, expected_hex_black)
        

    @test_settings
    def test_rgb_to_hex(self):

        color_filter = ColorFilter(self.matrix_filter)

        expected_hex_white = '#ffffff'
        hex_white = color_filter.rgb_to_hex(255,255,255)
        
        self.assertEqual(expected_hex_white, hex_white)

        expected_hex_black = '#000000ff'
        hex_black = color_filter.rgb_to_hex(0,0,0,1)
        
        self.assertEqual(hex_black, expected_hex_black)
        

    @test_settings
    def test_list_to_rgba_str(self):

        white = [255,255,255,1]

        color_filter = ColorFilter(self.matrix_filter)

        rgba_str = color_filter.list_to_rgba_str(white)
        expected_str = 'rgba(255,255,255,1)'

        self.assertEqual(rgba_str, expected_str)

        white_noalpha = [255,255,255]
        rgba_str_2 = color_filter.list_to_rgba_str(white)

        self.assertEqual(rgba_str, expected_str)
        

    # test both gradient and single color
    @test_settings
    def test_encoded_space_to_html(self):

        white = [255,255,255,1]

        color_filter = ColorFilter(self.matrix_filter)

        html = color_filter.encoded_space_to_html(white)
        expected_html = 'rgba(255,255,255,1)'

        self.assertEqual(html, expected_html)

        # gradient
        gradient = [[0,0,0,1],[255,255,255,1]]
        gradient_html = color_filter.encoded_space_to_html(gradient)
        expected_gradient_html = 'linear-gradient(to right, rgba(0,0,0,1),rgba(255,255,255,1))'

        self.assertEqual(gradient_html, expected_gradient_html)


    @test_settings
    def test_decode(self):

        white = [255,255,255,1]

        color_filter = ColorFilter(self.matrix_filter)

        html = color_filter.decode(white)
        expected_html = 'rgba(255,255,255,1)'

        self.assertEqual(html, expected_html)

        # gradient
        gradient = [[0,0,0,1],[255,255,255,1]]
        gradient_html = color_filter.decode(gradient)
        expected_gradient_html = 'linear-gradient(to right, rgba(0,0,0,1),rgba(255,255,255,1))'

        self.assertEqual(gradient_html, expected_gradient_html)


    @test_settings
    def test_get_choices(self):

        # empty
        color_filter = ColorFilter(self.matrix_filter)
        choices = color_filter._get_choices()

        self.assertEqual(choices, [])

        # with spaces, 1 color, gradient
        space_1 = self.create_space([111,222,255,1])
        
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_2 = self.create_space(gradient)

        choices = color_filter._get_choices()
        expected_choices = [
            ('[111, 222, 255, 1]', 'rgba(111,222,255,1)', {
                'modify':True,
                'space_id':space_1.id,
                'description' : None,
                'gradient' : False,
            }),
            ('[[0, 0, 0, 1], [255, 255, 255, 1]]', 'linear-gradient(to right, rgba(0,0,0,1),rgba(255,255,255,1))', {
                'modify' : True,
                'space_id' : space_2.id,
                'description' : None,
                'gradient': True,
            })
        ]

        self.assertEqual(choices, expected_choices)

    @test_settings
    def test_get_matrix_form_field(self):

        # empty
        color_filter = ColorFilter(self.matrix_filter)
        field = color_filter.get_matrix_form_field()
        self.assertEqual(field.choices, [])
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertTrue(isinstance(field.widget, SliderRadioSelectColor))
        
        # with choices
        space_1 = self.create_space([111,222,255,1])
        
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_2 = self.create_space(gradient)

        self.matrix_filter.refresh_from_db()
        color_filter = ColorFilter(self.matrix_filter)
        field = color_filter.get_matrix_form_field()

        expected_choices = [
            ('[111, 222, 255, 1]', 'rgba(111,222,255,1)', {
                'modify':True,
                'space_id':space_1.id,
                'description' : None,
                'gradient' : False,
            }),
            ('[[0, 0, 0, 1], [255, 255, 255, 1]]', 'linear-gradient(to right, rgba(0,0,0,1),rgba(255,255,255,1))', {
                'modify' : True,
                'space_id' : space_2.id,
                'description' : None,
                'gradient': True,
            })
        ]
        
        self.assertEqual(field.choices, expected_choices)
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertTrue(isinstance(field.widget, SliderRadioSelectColor))

        # with multiple values
        self.matrix_filter.definition = {
            'allow_multiple_values' : True,
        }

        self.matrix_filter.save()
        color_filter = ColorFilter(self.matrix_filter)

        field = color_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.MultipleChoiceField))
        self.assertTrue(isinstance(field.widget, SliderSelectMultipleColors))
        

    @test_settings
    def test_get_node_space_definition_form_field(self):

        # empty
        color_filter = ColorFilter(self.matrix_filter)
        from_url = '/test-url/'
        field = color_filter.get_node_space_definition_form_field(from_url)

        self.assertTrue(isinstance(field, ObjectLabelModelMultipleChoiceField))
        self.assertTrue(isinstance(field.widget, DefineColorsWidget))

        # with space
        space_1 = self.create_space([111,222,255,1])
        
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_2 = self.create_space(gradient)

        field = color_filter.get_node_space_definition_form_field(from_url)
        self.assertTrue(isinstance(field, ObjectLabelModelMultipleChoiceField))
        self.assertTrue(isinstance(field.widget, DefineColorsWidget))
        

    @test_settings
    def test_get_encoded_space_from_form(self):

        color_filter = ColorFilter(self.matrix_filter)

        form = ColorFilterManagementForm(self.root_meta_node, self.root_node, data={})
        encoded_space = color_filter.get_encoded_space_from_form(form)
        self.assertEqual(encoded_space, [])
        

    @test_settings
    def test_get_space_initial(self):

        color_filter = ColorFilter(self.matrix_filter)

        initial = color_filter.get_space_initial()
        self.assertEqual(initial, {})
        

    @test_settings
    def test_get_single_space_initial(self):

        color_filter = ColorFilter(self.matrix_filter)
        space_1 = self.create_space([111,222,255,1])

        initial = color_filter.get_single_space_initial(space_1)

        expected_initial = {
            'color' : '#6fdeff',
        }

        self.assertEqual(expected_initial, initial)

        # gradient
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_2 = self.create_space(gradient)

        initial_2 = color_filter.get_single_space_initial(space_2)

        expected_initial_2 = {
            'color' : '#000000',
            'color_2' : '#ffffffff',
            'gradient' : True,
        }

        self.assertEqual(initial_2, expected_initial_2)


    @test_settings
    def test_save_single_space(self):

        # create
        color_filter = ColorFilter(self.matrix_filter)

        data = {
            'input_language' : 'en',
            'color' : '#000000',
        }

        form = ColorFilterSpaceForm(data=data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        space = color_filter.save_single_space(form)
        self.assertEqual(space.matrix_filter, self.matrix_filter)
        self.assertEqual(space.encoded_space, [0,0,0,1])        

        # edit
        data_2 = {
            'input_language' : 'en',
            'color' : '#ff00ff',
            'color_2': '#00ff00',
            'description' : 'rainbow',
            'gradient' : True,
        }

        form_2 = ColorFilterSpaceForm(data=data_2)

        is_valid = form_2.is_valid()
        self.assertEqual(form_2.errors, {})

        space_2 = color_filter.save_single_space(form_2)
        self.assertEqual(space_2.matrix_filter, self.matrix_filter)
        self.assertEqual(space_2.encoded_space, [[255,0,255,1],[0,255,0,1]])
        self.assertEqual(space_2.additional_information['description'], 'rainbow')
        self.assertEqual(space_2.additional_information['gradient'], True)
        
        
    @test_settings
    def test_get_node_filter_space_as_list(self):

        child = self.create_node(self.root_node, 'Child')

        color_filter = ColorFilter(self.matrix_filter)
        space_1 = self.create_space([111,222,255,1])

        # gradient
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_2 = self.create_space(gradient)

        node_filter_space = NodeFilterSpace(
            node=child,
            matrix_filter = self.matrix_filter,
        )

        node_filter_space.save()

        node_filter_space.values.add(space_1)

        
        space_list = color_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, [[111,222,255,1]])

        node_filter_space.values.add(space_2)

        space_list = color_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, [[111,222,255,1], [[0,0,0,1],[255,255,255,1]]])
        

    @test_settings
    def test_validate_single_color(self):

        color_filter = ColorFilter(self.matrix_filter)

        invalid_colors = ['a', 1, [], [1,2,3],[0,0,256,1],[-1,0,0,1],[0,0,0,2]]

        for invalid_color in invalid_colors:
            is_valid = color_filter.validate_single_color(invalid_color)
            self.assertFalse(is_valid)

        valid_color = [0,255,123,1]
        is_valid = color_filter.validate_single_color(valid_color)
        self.assertTrue(is_valid)


    @test_settings
    def test_validate_encoded_space(self):

        color_filter = ColorFilter(self.matrix_filter)

        invalid_encoded_spaces = [1,'a',[],[[1,2,3,1],[]], [355,1,1,1]]

        for invalid_space in invalid_encoded_spaces:
            is_valid = color_filter.validate_encoded_space(invalid_space)
            self.assertFalse(is_valid)


        valid_encoded_spaces = [[111,222,255,1], [[0,0,0,0],[255,255,255,1]] ]

        for space in valid_encoded_spaces:
            is_valid = color_filter.validate_encoded_space(space)
            self.assertTrue(is_valid)
            
        

class TestDescriptiveTextAndImagesFilter(MatrixFilterTestCommon, WithNatureGuide, WithMatrixFilters,
                                         TenantTestCase):

    def setUp(self):
        super().setUp()

        filter_kwargs = {
            'definition' : {
                'allow_multiple_values' : False,
            }
        }

        self.matrix_filter = self.create_matrix_filter('DTAI Filter', self.root_meta_node,
                                                       'DescriptiveTextAndImagesFilter', **filter_kwargs)


    def create_space(self, text):
        
        matrix_filter_space = MatrixFilterSpace(
            matrix_filter = self.matrix_filter,
            encoded_space = text,
        )

        matrix_filter_space.save()

        return matrix_filter_space


    def check_field_classes(self, dtai_filter):

        self.assertEqual(dtai_filter.MatrixSingleChoiceFormFieldClass, forms.ChoiceField)
        self.assertEqual(dtai_filter.MatrixMultipleChoiceFormFieldClass, forms.MultipleChoiceField)

        self.assertEqual(dtai_filter.MatrixSingleChoiceWidgetClass, SliderRadioSelectDescriptor)
        self.assertEqual(dtai_filter.MatrixMultipleChoiceWidgetClass, SliderSelectMultipleDescriptors)

        self.assertEqual(dtai_filter.NodeSpaceDefinitionFormFieldClass, ObjectLabelModelMultipleChoiceField)
        self.assertEqual(dtai_filter.NodeSpaceDefinitionWidgetClass, DefineDescriptionWidget)

        self.assertEqual(dtai_filter.matrix_filter, self.matrix_filter)


        if self.matrix_filter.definition and self.matrix_filter.definition.get('allow_multiple_values', False) == False:
            self.assertEqual(dtai_filter.MatrixFormFieldClass, forms.ChoiceField)
            self.assertEqual(dtai_filter.MatrixFormFieldWidget, SliderRadioSelectDescriptor)

        else:
            self.assertEqual(dtai_filter.MatrixFormFieldClass, forms.MultipleChoiceField)
            self.assertEqual(dtai_filter.MatrixFormFieldWidget, SliderSelectMultipleDescriptors)


    # test both single space and multispace
    @test_settings
    def test_init_no_encoded_space(self):

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        self.assertTrue(dtai_filter.is_multispace)
        
        self.check_field_classes(dtai_filter)

        # no encoded space, so set_encoded_space
        expected_space = []
        self.assertEqual(dtai_filter.matrix_filter.encoded_space, expected_space)


    @test_settings
    def test_init_with_encoded_space(self):
        space_1 = self.create_space('pattern 1')
        space_2 = self.create_space('pattern 2')

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        expected_space = ['pattern 1', 'pattern 2']
        self.assertEqual(dtai_filter.matrix_filter.encoded_space, expected_space)

        # test multiple values
        self.matrix_filter.definition = {
            'allow_multiple_values' : True,
        }

        self.matrix_filter.save()

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)
        self.assertTrue(self.matrix_filter.definition.get('allow_multiple_values', False))

        self.check_field_classes(dtai_filter)


    @test_settings
    def test_get_default_definition(self):

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        definition = dtai_filter.get_default_definition()
        self.assertEqual(definition, {})


    @test_settings
    def test_get_choices(self):

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        # empty
        choices = dtai_filter._get_choices()
        self.assertEqual(choices, [])

        # with choices
        space_1 = self.create_space('pattern 1')
        space_2 = self.create_space('pattern 2')

        choices = dtai_filter._get_choices()
        expected_choices = [
            ('pattern 1', 'pattern 1', {'image': None, 'modify':True, 'space_id': space_1.id}),
            ('pattern 2', 'pattern 2', {'image': None, 'modify':True, 'space_id': space_2.id})
        ]

        self.assertEqual(choices, expected_choices)


    @test_settings
    def test_get_matrix_form_field(self):
        
        # empty, single choices
        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        field = dtai_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertTrue(isinstance(field.widget, SliderRadioSelectDescriptor))

        # empty, multiple choices
        dtai_filter.matrix_filter.definition = {
            'allow_multiple_values' : True
        }
        dtai_filter.matrix_filter.save()

        self.matrix_filter.refresh_from_db()
        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        field = dtai_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.MultipleChoiceField))
        self.assertTrue(isinstance(field.widget, SliderSelectMultipleDescriptors))
        self.assertEqual(field.choices, [])

        # with choices
        dtai_filter.matrix_filter.definition = {
            'allow_multiple_values' : False
        }
        dtai_filter.matrix_filter.save()
        self.matrix_filter.refresh_from_db()
        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        space_1 = self.create_space('pattern 1')
        space_2 = self.create_space('pattern 2')

        expected_choices = [
            ('pattern 1', 'pattern 1', {'image': None, 'modify':True, 'space_id': space_1.id}),
            ('pattern 2', 'pattern 2', {'image': None, 'modify':True, 'space_id': space_2.id})
        ]

        field = dtai_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertTrue(isinstance(field.widget, SliderRadioSelectDescriptor))
        self.assertEqual(field.choices, expected_choices)

        # choices, multiple allowed
        dtai_filter.matrix_filter.definition = {
            'allow_multiple_values' : True
        }
        dtai_filter.matrix_filter.save()

        self.matrix_filter.refresh_from_db()
        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        field = dtai_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.MultipleChoiceField))
        self.assertTrue(isinstance(field.widget, SliderSelectMultipleDescriptors))
        
        self.assertEqual(field.choices, expected_choices)


    @test_settings
    def test_get_node_space_definition_form_field(self):

        from_url = '/test-url/'
        
        # empty
        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        field = dtai_filter.get_node_space_definition_form_field(from_url)
        self.assertTrue(isinstance(field, ObjectLabelModelMultipleChoiceField))
        self.assertTrue(isinstance(field.widget, DefineDescriptionWidget))

        # with choices
        space_1 = self.create_space('pattern 1')
        space_2 = self.create_space('pattern 2')

        field = dtai_filter.get_node_space_definition_form_field(from_url)
        self.assertTrue(isinstance(field, ObjectLabelModelMultipleChoiceField))
        self.assertTrue(isinstance(field.widget, DefineDescriptionWidget))
        

    @test_settings
    def test_get_encoded_space_from_form(self):

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)
        form = DescriptiveTextAndImagesFilterSpaceForm()

        space = dtai_filter.get_encoded_space_from_form(form)
        self.assertEqual(space, [])


    @test_settings
    def test_get_space_initial(self):
        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        initial = dtai_filter.get_space_initial()
        
        self.assertEqual(initial, {})
        

    @test_settings
    def test_get_single_space_initial(self):

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)
        space_1 = self.create_space('pattern 1')

        initial = dtai_filter.get_single_space_initial(space_1)
        expected_initial = {
            'text' : 'pattern 1',
        }

        self.assertEqual(initial, expected_initial)
        

    @test_settings
    def test_save_single_space(self):

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        text = 'pattern a'

        # create
        data = {
            'input_language' : 'en',
            'text' : text,
        }

        form = DescriptiveTextAndImagesFilterSpaceForm(data=data)

        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})

        space = dtai_filter.save_single_space(form)

        self.assertEqual(space.matrix_filter, self.matrix_filter)
        self.assertEqual(space.encoded_space, text)
        
        # edit
        data['matrix_filter_space_id'] = space.id
        text_2 = 'updated pattern'
        data['text'] = text_2

        form = DescriptiveTextAndImagesFilterSpaceForm(data=data)
        is_valid = form.is_valid()

        space_2 = dtai_filter.save_single_space(form)

        self.assertEqual(space, space_2)
        self.assertEqual(space_2.encoded_space, text_2)
        

    @test_settings
    def test_get_node_filter_space_as_list(self):

        child = self.create_node(self.root_node, 'Child')

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        space_1 = self.create_space('pattern 1')
        space_2 = self.create_space('pattern 2')

        node_filter_space = NodeFilterSpace(
            node=child,
            matrix_filter = self.matrix_filter,
        )

        node_filter_space.save()

        node_filter_space.values.add(space_1)

        
        space_list = dtai_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, ['pattern 1'])

        node_filter_space.values.add(space_2)

        space_list = dtai_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, ['pattern 1', 'pattern 2'])


    @test_settings
    def test_validate_encoded_space(self):

        dtai_filter = DescriptiveTextAndImagesFilter(self.matrix_filter)

        invalid_spaces = [[],1]

        for invalid_space in invalid_spaces:

            is_valid = dtai_filter.validate_encoded_space(invalid_space)
            self.assertFalse(is_valid)

        valid_spaces = ['a', 'asfdergt rt hgrwth ', str(1)]
        

        for space in valid_spaces:
            is_valid = dtai_filter.validate_encoded_space(space)
            self.assertTrue(is_valid)



class TestTextOnlyFilter(MatrixFilterTestCommon, WithNatureGuide, WithMatrixFilters, TenantTestCase):
    

    def setUp(self):
        super().setUp()

        filter_kwargs = {
            'definition' : {
                'allow_multiple_values' : False,
            }
        }

        self.matrix_filter = self.create_matrix_filter('Text only Filter', self.root_meta_node,
                                                       'TextOnlyFilter', **filter_kwargs)


    def create_space(self, text):
        
        matrix_filter_space = MatrixFilterSpace(
            matrix_filter = self.matrix_filter,
            encoded_space = text,
        )

        matrix_filter_space.save()

        return matrix_filter_space


    def check_field_classes(self, text_filter):

        self.assertEqual(text_filter.MatrixSingleChoiceFormFieldClass, forms.ChoiceField)
        self.assertEqual(text_filter.MatrixMultipleChoiceFormFieldClass, forms.MultipleChoiceField)

        self.assertEqual(text_filter.MatrixSingleChoiceWidgetClass, SliderRadioSelectTextDescriptor)
        self.assertEqual(text_filter.MatrixMultipleChoiceWidgetClass, SliderSelectMultipleTextDescriptors)

        self.assertEqual(text_filter.NodeSpaceDefinitionFormFieldClass, ObjectLabelModelMultipleChoiceField)
        self.assertEqual(text_filter.NodeSpaceDefinitionWidgetClass, DefineTextDescriptionWidget)

        self.assertEqual(text_filter.matrix_filter, self.matrix_filter)


        if self.matrix_filter.definition and self.matrix_filter.definition.get('allow_multiple_values', False) == False:
            self.assertEqual(text_filter.MatrixFormFieldClass, forms.ChoiceField)
            self.assertEqual(text_filter.MatrixFormFieldWidget, SliderRadioSelectTextDescriptor)

        else:
            self.assertEqual(text_filter.MatrixFormFieldClass, forms.MultipleChoiceField)
            self.assertEqual(text_filter.MatrixFormFieldWidget, SliderSelectMultipleTextDescriptors)


    # test both single space and multispace
    @test_settings
    def test_init_no_encoded_space(self):

        text_filter = TextOnlyFilter(self.matrix_filter)

        self.assertTrue(text_filter.is_multispace)
        
        self.check_field_classes(text_filter)

        # no encoded space, so set_encoded_space
        expected_space = []
        self.assertEqual(text_filter.matrix_filter.encoded_space, expected_space)


    @test_settings
    def test_init_with_encoded_space(self):
        text_1 = 'text 1. Can be long.'
        text_2 = 'text 2. Can be long, too.'
        
        space_1 = self.create_space(text_1)
        space_2 = self.create_space(text_2)

        text_filter = TextOnlyFilter(self.matrix_filter)

        expected_space = [text_1, text_2]
        self.assertEqual(text_filter.matrix_filter.encoded_space, expected_space)

        # test multiple values
        self.matrix_filter.definition = {
            'allow_multiple_values' : True,
        }

        self.matrix_filter.save()

        text_filter = TextOnlyFilter(self.matrix_filter)
        self.assertTrue(self.matrix_filter.definition.get('allow_multiple_values', False))

        self.check_field_classes(text_filter)


    @test_settings
    def test_get_choices(self):

        # empty
        text_filter = TextOnlyFilter(self.matrix_filter)

        choices = text_filter._get_choices()
        self.assertEqual(choices, [])

        # choices
        text_1 = 'text 1. Can be long.'
        text_2 = 'text 2. Can be long, too.'
        
        space_1 = self.create_space(text_1)
        space_2 = self.create_space(text_2)

        choices = text_filter._get_choices()

        expected_choices = [
            (text_1, text_1, {'modify':True,'space_id':space_1.id}),
            (text_2, text_2, {'modify':True,'space_id':space_2.id}),
        ]

        self.assertEqual(choices, expected_choices)


    @test_settings
    def test_get_matrix_form_field(self):

        # empty, single choice
        text_filter = TextOnlyFilter(self.matrix_filter)

        field = text_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertTrue(isinstance(field.widget, SliderRadioSelectTextDescriptor))

        # empty, multiple choice
        text_filter.matrix_filter.definition = {
            'allow_multiple_values' : True,
        }
        text_filter.matrix_filter.save()

        self.matrix_filter.refresh_from_db()
        text_filter = TextOnlyFilter(self.matrix_filter)

        field = text_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.MultipleChoiceField))
        self.assertTrue(isinstance(field.widget, SliderSelectMultipleTextDescriptors))

        # choices
        text_1 = 'text 1. Can be long.'
        text_2 = 'text 2. Can be long, too.'
        
        space_1 = self.create_space(text_1)
        space_2 = self.create_space(text_2)


        expected_choices = [
            (text_1, text_1, {'modify':True,'space_id':space_1.id}),
            (text_2, text_2, {'modify':True,'space_id':space_2.id}),
        ]

        text_filter.matrix_filter.definition = {
            'allow_multiple_values' : False,
        }
        text_filter.matrix_filter.save()

        self.matrix_filter.refresh_from_db()
        text_filter = TextOnlyFilter(self.matrix_filter)

        field = text_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertTrue(isinstance(field.widget, SliderRadioSelectTextDescriptor))
        self.assertEqual(field.choices, expected_choices)


        # choices, multiple allowed
        text_filter.matrix_filter.definition = {
            'allow_multiple_values' : True,
        }
        text_filter.matrix_filter.save()

        self.matrix_filter.refresh_from_db()
        text_filter = TextOnlyFilter(self.matrix_filter)

        field = text_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.MultipleChoiceField))
        self.assertTrue(isinstance(field.widget, SliderSelectMultipleTextDescriptors))
        self.assertEqual(field.choices, expected_choices)


    @test_settings
    def test_get_node_filter_space_as_list(self):

        child = self.create_node(self.root_node, 'Child')

        text_filter = TextOnlyFilter(self.matrix_filter)

        text_1 = 'text 1. Can be long.'
        text_2 = 'text 2. Can be long, too.'
        
        space_1 = self.create_space(text_1)
        space_2 = self.create_space(text_2)

        node_filter_space = NodeFilterSpace(
            node=child,
            matrix_filter = self.matrix_filter,
        )

        node_filter_space.save()

        node_filter_space.values.add(space_1)

        
        space_list = text_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, [text_1])

        node_filter_space.values.add(space_2)

        space_list = text_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, [text_1, text_2])


    @test_settings
    def test_get_encoded_space_from_form(self):

        text_filter = TextOnlyFilter(self.matrix_filter)
        form = TextOnlyFilterSpaceForm()

        space = text_filter.get_encoded_space_from_form(form)
        self.assertEqual(space, [])


    @test_settings
    def test_get_space_initial(self):

        text_filter = TextOnlyFilter(self.matrix_filter)

        initial = text_filter.get_space_initial()
        self.assertEqual(initial, {})


    @test_settings
    def test_get_single_space_initial(self):

        text_filter = TextOnlyFilter(self.matrix_filter)

        text_1 = 'text 1. Can be long.'
        
        space_1 = self.create_space(text_1)

        space_initial = text_filter.get_single_space_initial(space_1)
        expected_initial = {
            'text' : text_1,
        }

        self.assertEqual(space_initial, expected_initial)


    @test_settings
    def test_save_single_space(self):

        text_filter = TextOnlyFilter(self.matrix_filter)
        
        text_1 = 'text 1. Can be long.'

        # create
        data = {
            'input_language' : 'en',
            'text' : text_1,
        }
        form = TextOnlyFilterSpaceForm(data=data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        space = text_filter.save_single_space(form)
        self.assertEqual(space.matrix_filter, self.matrix_filter)
        self.assertEqual(space.encoded_space, text_1)

        # edit
        text_2 = 'updated text'
        data['text'] = text_2
        data['matrix_filter_space_id'] = space.id

        form = TextOnlyFilterSpaceForm(data=data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        space_2 = text_filter.save_single_space(form)
        self.assertEqual(space_2.matrix_filter, self.matrix_filter)
        self.assertEqual(space_2.encoded_space, text_2)

        self.assertEqual(space, space_2)


    @test_settings
    def test_get_node_space_definition_form_field(self):

        from_url = '/test-url/'
        
        # empty
        text_filter = TextOnlyFilter(self.matrix_filter)

        field = text_filter.get_node_space_definition_form_field(from_url)
        self.assertTrue(isinstance(field, ObjectLabelModelMultipleChoiceField))
        self.assertTrue(isinstance(field.widget, DefineTextDescriptionWidget))

        # with choices
        space_1 = self.create_space('text 1')
        space_2 = self.create_space('text 2')

        field = text_filter.get_node_space_definition_form_field(from_url)
        self.assertTrue(isinstance(field, ObjectLabelModelMultipleChoiceField))
        self.assertTrue(isinstance(field.widget, DefineTextDescriptionWidget))
        

    @test_settings
    def test_get_node_filter_space_as_list(self):

        child = self.create_node(self.root_node, 'Child')

        text_1 = 'text 1. Can be long.'
        text_2 = 'text 2. Can be long, too.'

        text_filter = TextOnlyFilter(self.matrix_filter)

        space_1 = self.create_space(text_1)
        space_2 = self.create_space(text_2)

        node_filter_space = NodeFilterSpace(
            node=child,
            matrix_filter = self.matrix_filter,
        )

        node_filter_space.save()

        node_filter_space.values.add(space_1)

        
        space_list = text_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, [text_1])

        node_filter_space.values.add(space_2)

        space_list = text_filter.get_node_filter_space_as_list(node_filter_space)
        self.assertEqual(space_list, [text_1, text_2])

    
    @test_settings
    def test_validate_encoded_space(self):

        text_filter = TextOnlyFilter(self.matrix_filter)

        invalid_spaces = [1, []]

        for invalid_space in invalid_spaces:
            is_valid = text_filter.validate_encoded_space(invalid_space)
            self.assertFalse(is_valid)

        valid_spaces = ['a', str(1)]

        for space in valid_spaces:
            is_valid = text_filter.validate_encoded_space(space)
            self.assertTrue(is_valid)
            
    


class TestTaxonFilter(MatrixFilterTestCommon, WithNatureGuide, WithMatrixFilters, TenantTestCase):
    

    def setUp(self):
        super().setUp()

        filter_kwargs = {
            'definition' : {
                'allow_multiple_values' : False,
            }
        }

        self.matrix_filter = self.create_matrix_filter('Taxon Filter', self.root_meta_node,
                                                       'TaxonFilter', **filter_kwargs)

    def create_space(self, encoded_space):

        matrix_filter_space = MatrixFilterSpace(
            matrix_filter = self.matrix_filter,
            encoded_space = encoded_space,
        )

        matrix_filter_space.save()

        return matrix_filter_space
        
        
    def check_field_classes(self, taxon_filter):

        self.assertEqual(taxon_filter.MatrixSingleChoiceFormFieldClass, forms.ChoiceField)
        self.assertEqual(taxon_filter.MatrixMultipleChoiceFormFieldClass, forms.MultipleChoiceField)

        self.assertEqual(taxon_filter.MatrixSingleChoiceWidgetClass, SliderRadioSelectTaxonfilter)
        self.assertEqual(taxon_filter.MatrixMultipleChoiceWidgetClass, SliderSelectMultipleTaxonfilters)

        self.assertEqual(taxon_filter.NodeSpaceDefinitionFormFieldClass, None)
        self.assertEqual(taxon_filter.NodeSpaceDefinitionWidgetClass, None)

        self.assertEqual(taxon_filter.matrix_filter, self.matrix_filter)

        self.assertEqual(taxon_filter.MatrixFormFieldClass, forms.ChoiceField)
        self.assertEqual(taxon_filter.MatrixFormFieldWidget, SliderRadioSelectTaxonfilter)


    def get_encoded_space(self, lazy_taxon=None):

        is_custom = True

        if lazy_taxon == None:
            is_custom = False

            models = TaxonomyModelRouter('taxonomy.sources.col')
            animalia = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
            lazy_taxon = LazyTaxon(instance=animalia)

        encoded_space = [{
            "taxa": [
                {
                    "taxon_nuid": lazy_taxon.taxon_nuid,
                    "name_uuid": str(lazy_taxon.name_uuid),
                    "taxon_source": lazy_taxon.taxon_source,
                    "taxon_latname": lazy_taxon.taxon_latname,
                    "taxon_author" : lazy_taxon.taxon_author
                }
            ],
            "latname": lazy_taxon.taxon_latname,
            "is_custom": is_custom,
        }]

        return encoded_space



    # test both single space and multispace
    @test_settings
    def test_init_no_encoded_space(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        self.assertFalse(taxon_filter.is_multispace)
        
        self.check_field_classes(taxon_filter)

        # no encoded space, so set_encoded_space
        expected_space = []
        self.assertEqual(taxon_filter.matrix_filter.encoded_space, expected_space)

    

    @test_settings
    def test_init_with_encoded_space(self):

        encoded_space = self.get_encoded_space()
        
        space_1 = self.create_space(encoded_space)

        taxon_filter = TaxonFilter(self.matrix_filter)

        expected_space = encoded_space
        self.assertEqual(taxon_filter.matrix_filter.encoded_space, expected_space)
        

    @test_settings
    def test_get_node_space_definition_form_field(self):
        pass


    @test_settings
    def test_get_default_definition(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        definition = taxon_filter.get_default_definition()
        self.assertEqual(definition, {})


    @test_settings
    def test_get_empty_encoded_space(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        space = taxon_filter.get_empty_encoded_space()
        self.assertEqual(space, [])


    @test_settings
    def test_get_choices(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        # empty
        choices = taxon_filter._get_choices()
        self.assertEqual(choices, [])

        # with choice
        encoded_space = self.get_encoded_space()
        space_1 = self.create_space(encoded_space)

        self.matrix_filter.refresh_from_db()
        taxon_filter = TaxonFilter(self.matrix_filter)

        choices = taxon_filter._get_choices()
        
        taxonfilter_json = json.dumps(encoded_space[0])
        
        extra_kwargs = {
            'image' : static('app_kit/buttons/taxonfilters/Animalia.svg'),
            'is_custom' : False,
            'data_value' : space_1.encoded_space[0],
            'data_b64value' : b64encode(taxonfilter_json.encode('utf-8')).decode('utf-8'),
        }
        
        expected_choices = [
            ('Animalia', 'Animalia', extra_kwargs)
        ]
        
        self.assertEqual(choices[0][0], expected_choices[0][0])
        self.assertEqual(choices[0][1], expected_choices[0][1])
        self.assertEqual(choices[0][2]['image'], expected_choices[0][2]['image'])
        self.assertEqual(choices[0][2]['is_custom'], expected_choices[0][2]['is_custom'])
        self.assertEqual(choices[0][2]['data_value'], expected_choices[0][2]['data_value'])

        choices_b64_loaded = json.loads(b64decode(choices[0][2]['data_b64value']))
        expected_choices_b64_loaded = json.loads(b64decode(expected_choices[0][2]['data_b64value']))
        self.assertEqual(type(choices_b64_loaded), dict)
        self.assertEqual(choices_b64_loaded, expected_choices_b64_loaded)


    @test_settings
    def test_get_matrix_form_field(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        # empty
        field = taxon_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertTrue(isinstance(field.widget, SliderRadioSelectTaxonfilter))
        self.assertEqual(field.choices, [])

        # with choice
        encoded_space = self.get_encoded_space()
        space_1 = self.create_space(encoded_space)

        self.matrix_filter.refresh_from_db()
        taxon_filter = TaxonFilter(self.matrix_filter)

        field = taxon_filter.get_matrix_form_field()
        self.assertTrue(isinstance(field, forms.ChoiceField))
        self.assertTrue(isinstance(field.widget, SliderRadioSelectTaxonfilter))
        self.assertEqual(len(field.choices), 1)
        

    @test_settings
    def test_make_taxonfilter_taxon(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        models = TaxonomyModelRouter('taxonomy.sources.col')
        animalia = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        lazy_taxon = LazyTaxon(instance=animalia)

        taxonfilter_taxon = taxon_filter.make_taxonfilter_taxon(lazy_taxon)

        expected_taxon = {
            'taxon_source' : 'taxonomy.sources.col',
            'taxon_latname' : 'Animalia',
            'taxon_author' : lazy_taxon.taxon_author,
            'name_uuid' : lazy_taxon.name_uuid,
            'taxon_nuid' : '001',
        }

        self.assertEqual(taxonfilter_taxon, expected_taxon)
        

    @test_settings
    def test_make_taxonfilter_entry(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        models = TaxonomyModelRouter('taxonomy.sources.col')
        animalia = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        lazy_taxon = LazyTaxon(instance=animalia)

        taxonfilter_entry = taxon_filter.make_taxonfilter_entry('Animalia',['taxonomy.sources.col'])

        expected_entry = {
            "taxa": [
                {
                    "taxon_nuid": lazy_taxon.taxon_nuid,
                    "name_uuid": str(lazy_taxon.name_uuid),
                    "taxon_source": lazy_taxon.taxon_source,
                    "taxon_latname": lazy_taxon.taxon_latname,
                    "taxon_author" : lazy_taxon.taxon_author
                }
            ],
            "latname": lazy_taxon.taxon_latname,
            "is_custom": False,
        }

        self.assertEqual(taxonfilter_entry, expected_entry)
        

    @test_settings
    def test_get_encoded_space_from_form(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        # no custom taxon
        data = {
            'input_language' : 'en',
            'name' : 'Animalia',
            'filter_type' : 'TaxonFilter',
            'taxonomic_filters' : ['Animalia'],
            'add_custom_taxonomic_filter' : None, # or a taxon
        }

        form = TaxonFilterManagementForm(self.root_meta_node, self.matrix_filter, data=data)

        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})

        encoded_space = taxon_filter.get_encoded_space_from_form(form)

        models = TaxonomyModelRouter('taxonomy.sources.col')
        animalia = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        animalia_lazy_taxon = LazyTaxon(instance=animalia)
        expected_encoded_space = [
            {
                "taxa": [
                    {
                        "taxon_nuid": animalia_lazy_taxon.taxon_nuid,
                        "name_uuid": str(animalia_lazy_taxon.name_uuid),
                        "taxon_source": animalia_lazy_taxon.taxon_source,
                        "taxon_latname": animalia_lazy_taxon.taxon_latname,
                        "taxon_author" : animalia_lazy_taxon.taxon_author
                    }
                ],
                "latname": animalia_lazy_taxon.taxon_latname,
                "is_custom": False,
            }
        ]

        self.assertEqual(encoded_space, expected_encoded_space)

        # with custom taxon
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta')
        lacerta_lazy_taxon = LazyTaxon(instance=lacerta)

        data['add_custom_taxonomic_filter_0'] = lacerta_lazy_taxon.taxon_source
        data['add_custom_taxonomic_filter_1'] = lacerta_lazy_taxon.taxon_latname
        data['add_custom_taxonomic_filter_2'] = lacerta_lazy_taxon.taxon_author
        data['add_custom_taxonomic_filter_3'] = str(lacerta_lazy_taxon.name_uuid)
        data['add_custom_taxonomic_filter_4'] = lacerta_lazy_taxon.taxon_nuid

        form = TaxonFilterManagementForm(self.root_meta_node, self.matrix_filter, data=data)

        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})
        self.assertEqual(form.cleaned_data['add_custom_taxonomic_filter'], lacerta_lazy_taxon)

        encoded_space_2 = taxon_filter.get_encoded_space_from_form(form)

        expected_encoded_space_2 = expected_encoded_space.copy()
        expected_encoded_space_2.append(
            {
                "taxa": [
                    {
                        "taxon_nuid": lacerta_lazy_taxon.taxon_nuid,
                        "name_uuid": str(lacerta_lazy_taxon.name_uuid),
                        "taxon_source": lacerta_lazy_taxon.taxon_source,
                        "taxon_latname": lacerta_lazy_taxon.taxon_latname,
                        "taxon_author" : '',
                    }
                ],
                "latname": lacerta_lazy_taxon.taxon_latname,
                "is_custom": True,
            }
        )

        self.assertEqual(encoded_space_2[0], expected_encoded_space_2[0])
        self.assertEqual(encoded_space_2[1], expected_encoded_space_2[1])
        

    @test_settings
    def test_get_space_initial(self):

        taxon_filter = TaxonFilter(self.matrix_filter)
        
        # empty
        initial = taxon_filter.get_space_initial()
        self.assertEqual(initial, {'taxonomic_filters':[]})
        
        # with space
        encoded_space = self.get_encoded_space()
        space_1 = self.create_space(encoded_space)

        self.matrix_filter.refresh_from_db()
        taxon_filter = TaxonFilter(self.matrix_filter)

        initial = taxon_filter.get_space_initial()
        self.assertEqual(initial, {'taxonomic_filters':['Animalia']})

    @test_settings
    def test_validate_encoded_space(self):

        taxon_filter = TaxonFilter(self.matrix_filter)

        invalid_spaces = [1,'a']
        for invalid_space in invalid_spaces:
            is_valid = taxon_filter.validate_encoded_space(invalid_space)
            self.assertFalse(is_valid)

        valid_space = self.get_encoded_space()
        is_valid = taxon_filter.validate_encoded_space(valid_space)
        self.assertTrue(is_valid)


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
                    NumberFilterManagementForm, ColorFilterManagementForm)

from app_kit.features.nature_guides.matrix_filter_space_forms import ColorFilterSpaceForm

from app_kit.features.nature_guides.tests.common import WithNatureGuide, WithMatrixFilters

from app_kit.tests.mixins import WithMetaApp


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
        space_1 = self.create_space([111,222,333,1])
        space_2 = self.create_space([444,555,666,1])

        color_filter = ColorFilter(self.matrix_filter)

        expected_space = [[111,222,333,1],[444,555,666,1]]
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

        space_1 = self.create_space([111,222,333,1])
        space_2 = self.create_space([444,555,666,1])

        # multple spaces
        color_filter.set_encoded_space()
        expected_space = [[111,222,333,1],[444,555,666,1]]
        self.assertEqual(color_filter.matrix_filter.encoded_space, expected_space)

        # one gradient
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_3 = self.create_space(gradient)

        color_filter.set_encoded_space()
        expected_space_w_gradient = [[111,222,333,1],[444,555,666,1], [[0,0,0,1],[255,255,255,1]]]
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
        space_1 = self.create_space([111,222,333,1])
        
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_2 = self.create_space(gradient)

        choices = color_filter._get_choices()
        expected_choices = [
            ('[111, 222, 333, 1]', 'rgba(111,222,333,1)', {
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
        space_1 = self.create_space([111,222,333,1])
        
        gradient = [[0,0,0,1],[255,255,255,1]]
        space_2 = self.create_space(gradient)

        self.matrix_filter.refresh_from_db()
        color_filter = ColorFilter(self.matrix_filter)
        field = color_filter.get_matrix_form_field()

        expected_choices = [
            ('[111, 222, 333, 1]', 'rgba(111,222,333,1)', {
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
        space_1 = self.create_space([111,222,333,1])
        
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
        space_1 = self.create_space([111,222,333,1])

        initial = color_filter.get_single_space_initial(space_1)

        expected_initial = {
            'color' : '#6fde14',
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

        color_filter = ColorFilter(self.matrix_filter)

        form = ColorFilterSpaceForm()


    @test_settings
    def test_get_node_filter_space_as_list(self):
        pass


    @test_settings
    def test_validate_single_color(self):
        pass


    @test_settings
    def test_validate_encoded_space(self):
        pass
    

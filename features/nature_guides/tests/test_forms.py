from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import BLANK_CHOICE_DASH

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import WithMetaApp

from app_kit.features.nature_guides.tests.common import WithMatrixFilters, WithNatureGuide

from app_kit.features.nature_guides.forms import (IdentificationMatrixForm, SearchForNodeForm,
        NatureGuideOptionsForm, ManageNodelinkForm, MoveNodeForm)

from app_kit.features.nature_guides.matrix_filter_space_forms import ColorFilterSpaceForm

from app_kit.features.nature_guides.models import (MatrixFilter, MatrixFilterSpace, NodeFilterSpace,
                                                   NatureGuideCrosslinks)

from app_kit.features.taxon_profiles.models import TaxonProfiles

from app_kit.models import MetaAppGenericContent
from app_kit.features.generic_forms.models import GenericForm

from taxonomy.lazy import LazyTaxonList, LazyTaxon
from taxonomy.models import TaxonomyModelRouter


class TestIdentificationMatrixForm(WithNatureGuide, WithMatrixFilters, TenantTestCase):

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First')

        matrix_filters = self.create_all_matrix_filters(node)

        form = IdentificationMatrixForm(node.meta_node)

        for matrix_filter in MatrixFilter.objects.filter(meta_node=node.meta_node):

            self.assertTrue(str(matrix_filter.uuid) in form.fields)
            
        

class TestNatureGuideOptionsForm(WithNatureGuide, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()

        # add an observatoin form and test if both TaxonProfiles and ObservationForm appear in choices
        observation_form = GenericForm.objects.create('Test observation form', 'en')
        content_type = ContentType.objects.get_for_model(observation_form)
        app_link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=content_type,
            object_id=observation_form.id,
        )
        app_link.save()

        form = NatureGuideOptionsForm(meta_app=self.meta_app, generic_content=nature_guide)

        taxon_profiles_content_type = ContentType.objects.get_for_model(TaxonProfiles)
        taxon_profiles_link = MetaAppGenericContent.objects.get(content_type=taxon_profiles_content_type)
        taxon_profiles = taxon_profiles_link.generic_content
        
        self.assertIn('result_action', form.fields)

        result_action_field = form.fields['result_action']
        self.assertEqual(len(result_action_field.choices), 3)

        choices = set([choice[0] for choice in result_action_field.choices])
        expected_choices = set([str(observation_form.uuid), str(taxon_profiles.uuid), BLANK_CHOICE_DASH[0]])


class TestManageNodelinkForm(WithNatureGuide, WithMatrixFilters, TenantTestCase):

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node

        from_url = '/'

        # form without node (-> create new link) and without matrix filters
        form = ManageNodelinkForm(parent_node, from_url=from_url)

        self.assertEqual(len(form.fields), 6)
        self.assertEqual(form.from_url, from_url)
        self.assertEqual(form.node, None)

        # for without node, but with all matrix filters
        matrix_filters = self.create_all_matrix_filters(parent_node)

        form = ManageNodelinkForm(parent_node, from_url=from_url)
        # taxon filter does not return a form field
        self.assertEqual(len(form.fields), 11)
        self.assertEqual(form.from_url, from_url)
        self.assertEqual(form.node, None)

        # test matrix filter fields
        for matrix_filter in matrix_filters:

            if matrix_filter.filter_type != 'TaxonFilter':
                self.assertIn(str(matrix_filter.uuid), form.fields)

                field = form.fields[str(matrix_filter.uuid)]
                self.assertEqual(field.label, matrix_filter.name)
                self.assertTrue(field.is_matrix_filter)
                self.assertEqual(field.matrix_filter, matrix_filter)
                self.assertEqual(field.initial, None)
                self.assertFalse(field.required)

            else:
                self.assertFalse(str(matrix_filter.uuid) in form.fields)

        # test with node (child)
        node = self.create_node(parent_node, 'First')
        form = ManageNodelinkForm(parent_node, from_url=from_url, node=node)
        # taxon filter does not return a form field
        self.assertEqual(len(form.fields), 11)
        self.assertEqual(form.node, node)
        self.assertEqual(form.from_url, from_url)


    @test_settings
    def test_get_matrix_filter_field_initial(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        matrix_filters = self.create_all_matrix_filters(parent_node)

        form = ManageNodelinkForm(parent_node, from_url='/')

        for field in form:
            if hasattr(field.field, 'is_matrix_filter') and field.field.is_matrix_filter == True:

                initial = form.get_matrix_filter_field_initial(field)
                self.assertEqual(initial, None)

        # add space for each node and filter
        node = self.create_node(parent_node, 'First')

        color_filter = MatrixFilter.objects.get(filter_type='ColorFilter', meta_node=parent_node.meta_node)
        color_space = MatrixFilterSpace.objects.get(matrix_filter=color_filter)

        dtai_filter = MatrixFilter.objects.get(filter_type='DescriptiveTextAndImagesFilter',
                                               meta_node=parent_node.meta_node)
        
        dtai_space = MatrixFilterSpace.objects.filter(matrix_filter=dtai_filter).first()

        textonly_filter = MatrixFilter.objects.get(filter_type='TextOnlyFilter',
                                               meta_node=parent_node.meta_node)
        textonly_space = MatrixFilterSpace.objects.filter(matrix_filter=textonly_filter).first()
        
        node_filter_spaces = {
            'ColorFilter' : color_space,
            'RangeFilter' : [5,6],
            'NumberFilter' : [1,3],
            'DescriptiveTextAndImagesFilter' : dtai_space,
            'TextOnlyFilter' : textonly_space,
        }

        for filter_type, space in node_filter_spaces.items():

            matrix_filter = MatrixFilter.objects.get(filter_type=filter_type, meta_node=parent_node.meta_node)

            node_space = NodeFilterSpace(
                node=node,
                matrix_filter=matrix_filter,
            )

            if filter_type in ['RangeFilter', 'NumberFilter']:
                node_space.encoded_space=space
                
            node_space.save()

            if filter_type not in ['RangeFilter', 'NumberFilter']:
                node_space.values.add(space)


        form = ManageNodelinkForm(parent_node, from_url='/', node=node)

        for field in form:
            if hasattr(field.field, 'is_matrix_filter') and field.field.is_matrix_filter == True:

                matrix_filter = field.field.matrix_filter

                initial = form.get_matrix_filter_field_initial(field.field)

                if matrix_filter.filter_type == 'RangeFilter':
                    self.assertEqual(initial, node_filter_spaces[matrix_filter.filter_type])
                elif matrix_filter.filter_type == 'NumberFilter':
                    expected = ['%g' %(float(i)) for i in node_filter_spaces[matrix_filter.filter_type]]
                    self.assertEqual(initial, expected)

                else:
                    filter_space = NodeFilterSpace.objects.get(matrix_filter=matrix_filter, node=node)
                    initial_values = [i.encoded_space for i in initial]
                    expected_initial = [y.encoded_space for y in filter_space.values.all()]
                    self.assertEqual(initial_values, expected_initial)


    @test_settings
    def test_clean(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        from_url = '/'

        # form without node (-> create new link) and without matrix filters
        form = ManageNodelinkForm(parent_node, from_url=from_url, data={})
        self.assertTrue(form.is_bound)

        self.assertFalse(form.is_valid())

        data = {
            'input_language' : 'en',
            'node_type' : 'node',
            'name' : 'name',
        }
        form = ManageNodelinkForm(parent_node, from_url=from_url, data=data)
        self.assertTrue(form.is_bound)

        form.is_valid()
        self.assertEqual(form.errors, {})


        data = {
            'input_language' : 'en',
            'node_type' : 'node',
            'decision_rule' : 'name',
        }
        form = ManageNodelinkForm(parent_node, from_url=from_url, data=data)
        self.assertTrue(form.is_bound)

        form.is_valid()
        #self.assertEqual(form.errors, {})
        self.assertIn('name', form.errors)
        

class TestMoveNodeForm(WithNatureGuide, TenantTestCase):

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()
        root_node = nature_guide.root_node
        
        left = self.create_node(root_node, 'Left')

        form = MoveNodeForm(left)
        self.assertEqual(form.child_node, left)

    @test_settings
    def test_clean(self):

        nature_guide = self.create_nature_guide()
        root_node = nature_guide.root_node
        
        left = self.create_node(root_node, 'Left')
        middle = self.create_node(root_node, 'Middle')
        right = self.create_node(root_node, 'Right')

        middle_1 = self.create_node(middle, 'Middle child')
        right_1 = self.create_node(right, 'Right child')

        # parent of this one will be moved
        crosslink = NatureGuideCrosslinks(
            parent=right_1,
            child=middle,
        )
        crosslink.save()

        crosslink_2 = NatureGuideCrosslinks(
            parent=middle_1,
            child=left,
        )

        crosslink_2.save()

        is_circular = right_1.move_to_check_crosslinks(left)

        self.assertTrue(is_circular)

        # test the form
        post_data = {
            'input_language' : 'en',
            'new_parent_node_id' : left.id,
        }

        form = MoveNodeForm(right_1, data=post_data)
        
        is_valid = form.is_valid()
        self.assertFalse(is_valid)
        self.assertIn('new_parent_node_id', form.errors)


        # test new parent equals old parent
        post_data_2 = {
            'input_language' : 'en',
            'new_parent_node_id' : right_1.parent.id,
        }

        form_2 = MoveNodeForm(right_1, data=post_data_2)
        
        is_valid_2 = form_2.is_valid()
        self.assertFalse(is_valid_2)
        self.assertIn('new_parent_node_id', form_2.errors)

from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import BLANK_CHOICE_DASH

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import WithMetaApp

from app_kit.features.nature_guides.tests.common import WithMatrixFilters, WithNatureGuide

from app_kit.features.nature_guides.forms import (IdentificationMatrixForm, SearchForNodeForm,
        NatureGuideOptionsForm, ManageNodelinkForm, MoveNodeForm, MatrixFilterValueChoicesMixin,
        ManageMatrixFilterRestrictionsForm)

from app_kit.features.nature_guides.matrix_filter_space_forms import ColorFilterSpaceForm

from app_kit.features.nature_guides.models import (MatrixFilter, MatrixFilterSpace, NodeFilterSpace,
                                                   NatureGuideCrosslinks, MatrixFilterRestriction)

from app_kit.features.taxon_profiles.models import TaxonProfiles

from app_kit.models import MetaAppGenericContent
from app_kit.features.generic_forms.models import GenericForm

from taxonomy.lazy import LazyTaxonList, LazyTaxon
from taxonomy.models import TaxonomyModelRouter


class TestIdentificationMatrixForm(WithNatureGuide, WithMatrixFilters, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First')

        matrix_filters = self.create_all_matrix_filters(node)

        form = IdentificationMatrixForm(self.meta_app, node.meta_node)

        for matrix_filter in MatrixFilter.objects.filter(meta_node=node.meta_node):

            self.assertTrue(str(matrix_filter.uuid) in form.fields)
            
        

class TestNatureGuideOptionsForm(WithNatureGuide, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()

        # add an observation form and test if both TaxonProfiles and ObservationForm appear in choices
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


class TestManageNodelinkForm(WithNatureGuide, WithMatrixFilters, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node

        from_url = '/'

        # form without node (-> create new link) and without matrix filters
        form = ManageNodelinkForm(self.meta_app, parent_node, parent_node, from_url=from_url)

        self.assertEqual(len(form.fields), 9)
        self.assertEqual(form.from_url, from_url)
        self.assertEqual(form.node, None)

        # for without node, but with all matrix filters
        matrix_filters = self.create_all_matrix_filters(parent_node)

        form = ManageNodelinkForm(self.meta_app, parent_node, parent_node, from_url=from_url)
        # taxon filter does not return a form field
        self.assertEqual(len(form.fields), 14)
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
        form = ManageNodelinkForm(self.meta_app, parent_node, parent_node, from_url=from_url, node=node)
        # taxon filter does not return a form field
        self.assertEqual(len(form.fields), 14)
        self.assertEqual(form.node, node)
        self.assertEqual(form.from_url, from_url)


    @test_settings
    def test_init_with_crosslink_parent(self):

        nature_guide = self.create_nature_guide()
        child_1 = self.create_node(nature_guide.root_node, 'child 1')
        child_2 = self.create_node(nature_guide.root_node, 'child 2')
        grandchild_1 = self.create_node(child_1, 'child 1 1')

        # assumed crosslink: grandchild_1 = parent, child_2 = child
        matrix_filters = self.create_all_matrix_filters(grandchild_1)

        submitted_parent_node = grandchild_1
        tree_parent_node = nature_guide.root_node

        
        from_url = '/'

        # form without node (-> create new link) and without matrix filters
        form = ManageNodelinkForm(self.meta_app, tree_parent_node, tree_parent_node, from_url=from_url)

        for field in form:
            self.assertFalse(getattr(field, 'is_matrix_filter', False))

        form = ManageNodelinkForm(self.meta_app, tree_parent_node, submitted_parent_node, from_url=from_url)

        matrix_filter_field_count = 0
        matrix_filter_uuids = [str(m.uuid) for m in matrix_filters]
        
        for field in form:
            if getattr(field.field, 'is_matrix_filter', None) != None:
                self.assertIn(str(field.field.matrix_filter.uuid), matrix_filter_uuids)
                matrix_filter_field_count += 1

        # -1, TaxonFilter is skipped
        self.assertEqual(matrix_filter_field_count, len(matrix_filters) - 1)


    @test_settings
    def test_get_matrix_filter_field_initial(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        matrix_filters = self.create_all_matrix_filters(parent_node)

        form = ManageNodelinkForm(self.meta_app, parent_node, parent_node, from_url='/')

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


        form = ManageNodelinkForm(self.meta_app, parent_node, parent_node, from_url='/', node=node)

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
        form = ManageNodelinkForm(self.meta_app, parent_node, parent_node, from_url=from_url, data={})
        self.assertTrue(form.is_bound)

        self.assertFalse(form.is_valid())

        data = {
            'input_language' : 'en',
            'node_type' : 'node',
            'name' : 'name',
            'morphotype' : 'morphotype',
        }
        form = ManageNodelinkForm(self.meta_app, parent_node, parent_node, from_url=from_url, data=data)
        self.assertTrue(form.is_bound)

        form.is_valid()
        self.assertEqual(form.errors, {})


        data = {
            'input_language' : 'en',
            'node_type' : 'node',
            'decision_rule' : 'name',
        }
        form = ManageNodelinkForm(self.meta_app, parent_node, parent_node, from_url=from_url, data=data)
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

        form = MoveNodeForm(left, root_node)
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

        form = MoveNodeForm(right_1, right, data=post_data)
        
        is_valid = form.is_valid()
        self.assertFalse(is_valid)
        self.assertIn('new_parent_node_id', form.errors)


        # test new parent equals old parent
        post_data_2 = {
            'input_language' : 'en',
            'new_parent_node_id' : right_1.parent.id,
        }

        form_2 = MoveNodeForm(right_1, right, data=post_data_2)
        
        is_valid_2 = form_2.is_valid()
        self.assertFalse(is_valid_2)
        self.assertIn('new_parent_node_id', form_2.errors)


    @test_settings
    def test_clean_crosslinks(self):
        
        nature_guide = self.create_nature_guide()
        nature_guide_2 = self.create_nature_guide('ng 2')
        root_node = nature_guide.root_node
        n2_root_node = nature_guide_2.root_node
        
        n2_left = self.create_node(n2_root_node, 'Left')
        middle = self.create_node(root_node, 'Middle')
        right = self.create_node(root_node, 'Right')

        right_1 = self.create_node(right, 'Right child')

        # parent of this one will be moved
        crosslink = NatureGuideCrosslinks(
            parent=middle,
            child=right_1,
        )
        crosslink.save()

        # move right_1 to left, right_1 is crosslink, but the old parent is not the crosslink parent
        post_data = {
            'input_language' : 'en',
            'new_parent_node_id' : n2_left.id,
        }

        form = MoveNodeForm(right_1, right, data=post_data)

        is_valid = form.is_valid()

        self.assertIn('new_parent_node_id', form.errors)
        self.assertEqual(form.errors['new_parent_node_id'][0],
            'Moving Right child to Left (ng 2) is forbidden because the branch contains crosslinks.')


        # move right_1 to left, right_1 is crosslink, the old parent IS the crosslink parent
        form_2 = MoveNodeForm(right_1, middle, data=post_data)

        is_valid_2 = form.is_valid()

        self.assertIn('new_parent_node_id', form_2.errors)
        self.assertEqual(form_2.errors['new_parent_node_id'][0],
            'Moving Right child to Left (ng 2) is forbidden because the branch contains crosslinks.')

        
        # move right to left, downstream contains crosslink
        form_3 = MoveNodeForm(right, root_node, data=post_data)

        is_valid_2 = form_3.is_valid()

        self.assertIn('new_parent_node_id', form_3.errors)
        self.assertEqual(form_3.errors['new_parent_node_id'][0],
            'Moving Right to Left (ng 2) is forbidden because the branch contains crosslinks.')



class MockMatrixFilterValueChoicesMixin(MatrixFilterValueChoicesMixin):

    def get_matrix_filter_field_initial(self, field):
        return None
    

class TestMatrixFilterValueChoicesMixin(WithNatureGuide, WithMatrixFilters, WithMetaApp, TenantTestCase):

    @test_settings
    def test_get_matrix_filters(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node

        # for without node, but with all matrix filters
        matrix_filters = self.create_all_matrix_filters(parent_node)

        mixin = MatrixFilterValueChoicesMixin()
        mixin.meta_node = meta_node

        mixin_matrix_filters = mixin.get_matrix_filters()
        self.assertEqual(list(mixin_matrix_filters), list(matrix_filters))
        

    @test_settings
    def test_add_matrix_filter_value_choices(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node

        # for without node, but with all matrix filters
        matrix_filters = self.create_all_matrix_filters(parent_node)

        mixin = MockMatrixFilterValueChoicesMixin()
        mixin.meta_app = self.meta_app
        mixin.meta_node = meta_node
        mixin.fields = {}
        mixin.from_url = '/'

        mixin.add_matrix_filter_value_choices()

        for matrix_filter in matrix_filters:

            matrix_filter_uuid = str(matrix_filter.uuid)

            if matrix_filter.filter_type == 'TaxonFilter':
                self.assertFalse(matrix_filter_uuid in mixin.fields)
            else:
                self.assertIn(matrix_filter_uuid, mixin.fields)
                field = mixin.fields[matrix_filter_uuid]

                self.assertFalse(field.required)
                self.assertTrue(field.is_matrix_filter)
                self.assertEqual(field.label, matrix_filter.name)
        
    
class TestManageMatrixFilterRestrictionsForm(WithNatureGuide, WithMatrixFilters, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node

        # for without node, but with all matrix filters
        matrix_filters = self.create_all_matrix_filters(parent_node)

        for matrix_filter in matrix_filters:
            form = ManageMatrixFilterRestrictionsForm(self.meta_app, matrix_filter, meta_node, from_url=('/'))

            # the matrix filter itself may not occur in choices
            self.assertEqual(form.meta_node, meta_node)
            self.assertEqual(form.matrix_filter, matrix_filter)

            for restrictive_matrix_filter in matrix_filters:

                restrictive_matrix_filter_uuid = str(restrictive_matrix_filter.uuid)

                if restrictive_matrix_filter == matrix_filter or restrictive_matrix_filter.filter_type == 'TaxonFilter':
                    self.assertFalse(restrictive_matrix_filter_uuid in form.fields)

                else:
                    self.assertIn(restrictive_matrix_filter_uuid, form.fields)
            

    @test_settings
    def test_get_matrix_filters(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node

        # for without node, but with all matrix filters
        matrix_filters = self.create_all_matrix_filters(parent_node)

        for matrix_filter in matrix_filters:
            
            form = ManageMatrixFilterRestrictionsForm(self.meta_app, matrix_filter, meta_node, from_url=('/'))

            form_matrix_filters = form.get_matrix_filters()

            for restrictive_matrix_filter in form_matrix_filters:

                self.assertTrue(str(restrictive_matrix_filter.uuid) != str(matrix_filter.uuid))


    @test_settings
    def test_get_matrix_filter_field_initial(self):
        
        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        matrix_filters = self.create_all_matrix_filters(parent_node)

        for matrix_filter in matrix_filters:
            form = ManageMatrixFilterRestrictionsForm(self.meta_app, matrix_filter, meta_node, from_url='/')

            for field in form:
                if hasattr(field.field, 'is_matrix_filter') and field.field.is_matrix_filter == True:

                    initial = form.get_matrix_filter_field_initial(field.field)
                    self.assertEqual(initial, None)


        color_filter = MatrixFilter.objects.get(filter_type='ColorFilter', meta_node=meta_node)
        color_space = MatrixFilterSpace.objects.get(matrix_filter=color_filter)

        dtai_filter = MatrixFilter.objects.get(filter_type='DescriptiveTextAndImagesFilter',
                                               meta_node=meta_node)
        
        dtai_space = MatrixFilterSpace.objects.filter(matrix_filter=dtai_filter).first()

        textonly_filter = MatrixFilter.objects.get(filter_type='TextOnlyFilter',
                                               meta_node=meta_node)
        textonly_space = MatrixFilterSpace.objects.filter(matrix_filter=textonly_filter).first()
        
        restriction_filter_spaces = {
            'ColorFilter' : color_space,
            'RangeFilter' : [5,6],
            'NumberFilter' : [1,3],
            'DescriptiveTextAndImagesFilter' : dtai_space,
            'TextOnlyFilter' : textonly_space,
        }

        for restricted_filter in matrix_filters:

            restrictive_matrix_filters = MatrixFilter.objects.all().exclude(pk=restricted_filter.pk).exclude(
                filter_type='TaxonFilter')

            for restrictive_matrix_filter in restrictive_matrix_filters:

                filter_type = restrictive_matrix_filter.filter_type
                space = restriction_filter_spaces[filter_type]

                restriction = MatrixFilterRestriction(
                    restricted_matrix_filter=restricted_filter,
                    restrictive_matrix_filter=restrictive_matrix_filter,
                )

                if filter_type in ['RangeFilter', 'NumberFilter']:
                    restriction.encoded_space=space
                    
                restriction.save()

                if filter_type not in ['RangeFilter', 'NumberFilter']:
                    restriction.values.add(space)


            
            form = ManageMatrixFilterRestrictionsForm(self.meta_app, restricted_filter, meta_node, from_url='/')

            for field in form:
                if hasattr(field.field, 'is_matrix_filter') and field.field.is_matrix_filter == True:

                    restrictive_matrix_filter = field.field.matrix_filter

                    initial = form.get_matrix_filter_field_initial(field.field)

                    if restrictive_matrix_filter.filter_type == 'RangeFilter':
                        self.assertEqual(initial, restriction_filter_spaces[
                            restrictive_matrix_filter.filter_type])
                        
                    elif restrictive_matrix_filter.filter_type == 'NumberFilter':
                        expected = ['%g' %(float(i)) for i in restriction_filter_spaces[
                            restrictive_matrix_filter.filter_type]]
                        self.assertEqual(initial, expected)

                    else:
                        filter_space = MatrixFilterRestriction.objects.get(
                            restricted_matrix_filter=restricted_filter,
                            restrictive_matrix_filter=restrictive_matrix_filter)
                        
                        initial_values = [i.encoded_space for i in initial]
                        expected_initial = [y.encoded_space for y in filter_space.values.all()]
                        self.assertEqual(initial_values, expected_initial)

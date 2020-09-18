from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings

from app_kit.features.nature_guides.models import (NatureGuide, MetaNode, CrosslinkManager,
            NatureGuidesTaxonTree, NatureGuidesTaxonSynonym, MatrixFilter, MatrixFilterSpace, NodeFilterSpace,
            NatureGuideCrosslinks, ChildrenCacheManager)


from app_kit.features.nature_guides.tests.common import WithNatureGuide

from app_kit.features.nature_guides.zip_import import NatureGuideZipImporter

from app_kit.features.nature_guides.matrix_filters import (MATRIX_FILTER_TYPES, RangeFilter, NumberFilter,
        ColorFilter, DescriptiveTextAndImagesFilter, TaxonFilter)

from taxonomy.lazy import LazyTaxonList, LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from taxonomy.utils import NuidManager

import uuid


class TestNatureGuide(WithNatureGuide, TenantTestCase):

    @test_settings
    def test_create(self):

        nature_guide = NatureGuide.objects.create('Test Nature Guide', 'en')

        # check if the MetaNode was created
        start_node_qry = MetaNode.objects.filter(nature_guide=nature_guide, node_type='root')
        self.assertTrue(start_node_qry.exists())
        self.assertEqual(start_node_qry.count(), 1)

        start_node = start_node_qry.first()
        self.assertEqual(start_node.name, nature_guide.name)

        # check for natureguidetaxontree root node
        root_tree_node_qry = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide,
                                                                  meta_node=start_node)
        self.assertTrue(root_tree_node_qry.exists())
        self.assertEqual(root_tree_node_qry.count(), 1)

        root_tree_node = root_tree_node_qry.first()
        self.assertEqual(root_tree_node.taxon_nuid, '001001')
        

    @test_settings
    def test_zip_import_class(self):
        nature_guide = self.create_nature_guide()

        ZipImportClass = nature_guide.zip_import_class
        self.assertEqual(ZipImportClass, NatureGuideZipImporter)


    @test_settings
    def test_root_node(self):
        nature_guide = NatureGuide.objects.create('Test Nature Guide', 'en')

        root_node = nature_guide.root_node

        expected_root_node = NatureGuidesTaxonTree.objects.get(nature_guide=nature_guide,
                                                              meta_node__node_type='root')

        self.assertEqual(root_node, expected_root_node)


    @test_settings
    def test_get_primary_localization(self):

        nature_guide = self.create_nature_guide()

        # add a node with decision_rule
        parent_node = nature_guide.root_node
        node_name = 'First node'
        decision_rule = 'first node decision rule'
        node = self.create_node(parent_node, node_name, **{'decision_rule':decision_rule})


        matrix_filter_name = 'Test Filter'
        matrix_filter_description = 'Test Filter description'
        mf_extra = {
            'description' : matrix_filter_description,
        }
        matrix_filter = self.create_matrix_filter(matrix_filter_name, node.meta_node,
                                                  'DescriptiveTextAndImagesFilter', **mf_extra)

        # create a matrix filter space
        space_name = 'Space name' 
        space = MatrixFilterSpace(
            matrix_filter=matrix_filter,
            encoded_space=space_name,
        )
        space.save()

        locale = nature_guide.get_primary_localization()
        self.assertEqual(locale[nature_guide.name], nature_guide.name)
        self.assertEqual(locale[node_name], node_name)
        self.assertEqual(locale[decision_rule], decision_rule)
        self.assertEqual(locale[matrix_filter_name], matrix_filter_name)
        self.assertEqual(locale[matrix_filter_description], matrix_filter_description)
        self.assertEqual(locale[space_name], space_name)
        

    @test_settings
    def test_crosslinks(self):
        nature_guide = self.create_nature_guide()

        # add a node with decision_rule
        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First')

        # add sibling of node
        node_sibling = self.create_node(parent_node, 'Second')

        # add child of node
        node_child_1 = self.create_node(node, 'First Child 1')
        node_child_2 = self.create_node(node, 'First Child 2')

        crosslink = NatureGuideCrosslinks(
            parent=node_child_1,
            child=node_sibling,
        )
        crosslink.save()

        crosslink_2 = NatureGuideCrosslinks(
            parent=node_child_2,
            child=node_sibling,
        )
        crosslink_2.save()

        crosslinks = nature_guide.crosslinks()
        expected_dic = {}
        expected_dic[node_child_1.taxon_nuid] = [node_sibling.taxon_nuid]
        expected_dic[node_child_2.taxon_nuid] = [node_sibling.taxon_nuid]
        

    @test_settings
    def test_taxa_and_higher_taxa(self):

        nature_guide = self.create_nature_guide()

        # add a node with decision_rule
        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First', **{'node_type':'result'})

        # add sibling of node, with taxon
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        
        node_sibling = self.create_node(parent_node, 'Second', **{'node_type':'result'})
        node_sibling.meta_node.taxon = lacerta_agilis
        node_sibling.meta_node.save()

        taxa = nature_guide.taxa()

        self.assertTrue(isinstance(taxa, LazyTaxonList))
        
        taxa_nuids = set([t.taxon_nuid for t in taxa])
        expected_nuids = set([lacerta_agilis.taxon_nuid, node.taxon_nuid])

        self.assertEqual(taxa_nuids, expected_nuids)
        
        # test higher taxa
        higher_taxa = nature_guide.higher_taxa()
        self.assertTrue(isinstance(higher_taxa, LazyTaxonList))
        self.assertEqual(higher_taxa.count(), 0)
        


class TestMetaNode(WithNatureGuide, TenantTestCase):

    @test_settings
    def test_create(self):

        nature_guide = self.create_nature_guide()

        meta_node = MetaNode(
            nature_guide=nature_guide,
            name='Name',
            node_type='node',
        )

        meta_node.save()


class TestNatureGuidesTaxonTree(WithNatureGuide, TenantTestCase):

    @test_settings
    def test_name(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        node = self.create_node(parent_node, node_name, **{'node_type':'result'})

        self.assertEqual(node.name, node_name)

        
    @test_settings
    def test_tree_descendants(self):
        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        node = self.create_node(parent_node, node_name)

        sibling = self.create_node(parent_node, 'Second')

        child = self.create_node(node, 'Child')

        tree_descendants = parent_node.tree_descendants

        ids = set([c.id for c in tree_descendants])
        expected_ids = set([node.id, sibling.id, child.id])

        self.assertEqual(ids, expected_ids)
        self.assertEqual(tree_descendants.count(), 3)
        
        
    @test_settings
    def test_tree_children(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        node = self.create_node(parent_node, node_name)

        sibling = self.create_node(parent_node, 'Second')

        child = self.create_node(node, 'Child')

        tree_children = parent_node.tree_children

        ids = set([c.id for c in tree_children])
        expected_ids = set([node.id, sibling.id])

        self.assertEqual(ids, expected_ids)
        self.assertEqual(tree_children.count(), 2)

        # test for node
        node_tree_children = node.tree_children
        self.assertEqual(node_tree_children[0], child)
        self.assertEqual(node_tree_children.count(), 1)
        

    @test_settings
    def test_crosslink_children(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        node = self.create_node(parent_node, node_name)

        sibling = self.create_node(parent_node, 'Second')

        child = self.create_node(node, 'Child')

        crosslink = NatureGuideCrosslinks(
            parent=child,
            child=sibling,
        )

        crosslink.save()

        children = child.crosslink_children
        self.assertEqual(children[0], sibling)
        self.assertEqual(len(children), 1)
        

    @test_settings
    def test_children(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        node = self.create_node(parent_node, node_name)

        sibling = self.create_node(parent_node, 'Second')

        child = self.create_node(node, 'Child')
        child_child = self.create_node(child, 'Child child')

        crosslink = NatureGuideCrosslinks(
            parent=child,
            child=sibling,
        )

        crosslink.save()

        children = child.children

        ids = set([c.id for c in children])
        expected_ids = set([child_child.id, sibling.id])
        self.assertEqual(len(children), 2)
        

    @test_settings
    def test_get_taxon_tree_fields(self):

        nature_guide = NatureGuide(
            primary_language = 'en',
            name='Test NG',
        )

        nature_guide.save()

        nuidmanager = NuidManager()
        nature_guide_nuid = nuidmanager.decimal_to_nuid(nature_guide.id)

        meta_node = MetaNode(
            nature_guide=nature_guide,
            name=nature_guide.name,
            node_type = 'root',
        )

        meta_node.save()

        root_node = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=meta_node,
        )

        taxon_tree_fields = root_node.get_taxon_tree_fields()

        self.assertEqual(taxon_tree_fields['taxon_nuid'], '{0}001'.format(nature_guide_nuid))
        self.assertEqual(taxon_tree_fields['taxon_latname'], nature_guide.name)
        self.assertEqual(taxon_tree_fields['is_root_taxon'], True)
        self.assertEqual(taxon_tree_fields['rank'], None)

        root_node.save(None)
        
        meta_node_2 = MetaNode(
            nature_guide=nature_guide,
            name='First',
            node_type = 'node',
        )

        meta_node_2.save()

        node = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=meta_node_2,
        )

        taxon_tree_fields = node.get_taxon_tree_fields(root_node)
        self.assertEqual(taxon_tree_fields['taxon_nuid'], '{0}001001'.format(nature_guide_nuid))
        self.assertEqual(taxon_tree_fields['taxon_latname'], node.name)
        self.assertEqual(taxon_tree_fields['is_root_taxon'], False)
        self.assertEqual(taxon_tree_fields['rank'], None)

        node.save(root_node)

        with self.assertRaises(ValueError):
            taxon_tree_fields = node.get_taxon_tree_fields(root_node)


    @test_settings
    def test_save(self):
        nature_guide = NatureGuide(
            primary_language = 'en',
            name='Test NG',
        )

        nature_guide.save()

        nuidmanager = NuidManager()
        nature_guide_nuid = nuidmanager.decimal_to_nuid(nature_guide.id)

        meta_node = MetaNode(
            nature_guide=nature_guide,
            name=nature_guide.name,
            node_type = 'root',
        )

        meta_node.save()

        root_node = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=meta_node,
        )

        root_node.save(None)

        self.assertEqual(root_node.taxon_nuid, '{0}001'.format(nature_guide_nuid))
        self.assertEqual(root_node.taxon_latname, nature_guide.name)
        self.assertEqual(root_node.is_root_taxon, True)
        self.assertEqual(root_node.rank, None)

        # check latname update
        updated_name = 'Updated name'
        meta_node.name = updated_name
        
        root_node.save(None)
        self.assertEqual(root_node.taxon_latname, updated_name)

        # check with passed parent != None
        meta_node_2 = MetaNode(
            nature_guide=nature_guide,
            name='First',
            node_type = 'result',
        )

        meta_node_2.save()

        node = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=meta_node_2,
        )
        node.save(root_node)

        self.assertEqual(node.taxon_nuid, '{0}001001'.format(nature_guide_nuid))
        self.assertEqual(node.taxon_latname, node.name)
        self.assertEqual(node.is_root_taxon, False)
        self.assertEqual(node.rank, None)

        # check valuerror: adding a child to a result
        meta_node_3 = MetaNode(
            nature_guide=nature_guide,
            name='Second',
            node_type = 'result',
        )

        meta_node_3.save()

        node_2 = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=meta_node_3,
        )

        with self.assertRaises(ValueError):
            node_2.save(node)


        # check save without decision rule AND node name
        meta_node_4 = MetaNode(
            nature_guide=nature_guide,
            node_type = 'result',
        )

        meta_node_4.save()

        node_3 = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=meta_node_4,
        )

        with self.assertRaises(ValueError):
            node_3.save(root_node)

        # saving with decision rule and without name should work
        node_3.decision_rule = 'test rule'
        node_3.save(root_node)
        

    @test_settings
    def test_delete(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        decision_rule = 'decision_rule'
        node = self.create_node(parent_node, node_name, **{'decision_rule':decision_rule})
        node_name_uuid = str(node.name_uuid)

        node_qry = NatureGuidesTaxonTree.objects.filter(decision_rule=decision_rule)
        meta_node_qry = MetaNode.objects.filter(name=node_name)

        with self.assertRaises(PermissionError):
            node.delete()

        self.assertTrue(node_qry.exists())
        self.assertTrue(meta_node_qry.exists())


        # node is still in cache
        meta_parent = node.parent.meta_node
        cache_manager = ChildrenCacheManager(meta_parent)
        cache_manager.add_or_update_child(node)

        cache = meta_parent.children_cache
        self.assertEqual(len(cache['items']), 1)
        self.assertEqual(cache['items'][0]['uuid'], node_name_uuid)

        node.delete(from_delete_branch=True)

        meta_parent.refresh_from_db()
        cache = meta_parent.children_cache
        self.assertEqual(len(cache['items']), 0)

        self.assertFalse(node_qry.exists())
        self.assertFalse(meta_node_qry.exists())


    @test_settings
    def test_delete_keep_meta_node(self):
        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        node = self.create_node(parent_node, 'First')

        meta_node_qry = MetaNode.objects.filter(name=node_name)

        node_2 = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=node.meta_node,
        )

        node_2.save(nature_guide.root_node)

        self.assertTrue(meta_node_qry.exists())
        
        node.delete(from_delete_branch=True)

        self.assertTrue(meta_node_qry.exists())
        

    @test_settings
    def test_delete_branch(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        node = self.create_node(parent_node, node_name)
        node_pk = node.pk

        child = self.create_node(node, 'Child')
        child_meta_node = child.meta_node
        
        child_child = self.create_node(child, 'Child child')
        child_child_meta_node = child_child.meta_node

        node.delete_branch()

        self.assertFalse(NatureGuidesTaxonTree.objects.filter(pk=node_pk).exists())
        self.assertFalse(NatureGuidesTaxonTree.objects.filter(pk=child.id).exists())
        self.assertFalse(NatureGuidesTaxonTree.objects.filter(pk=child_child.id).exists())

        self.assertFalse(MetaNode.objects.filter(pk=child_meta_node.pk).exists())
        self.assertFalse(MetaNode.objects.filter(pk=child_child_meta_node.pk).exists())


    @test_settings
    def test_str(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        node_name = 'First'
        node = self.create_node(parent_node, node_name)

        self.assertEqual(str(node), node_name)



class TestCrosslinkManager(WithNatureGuide, TenantTestCase):

    @test_settings
    def test_check_crosslink(self):

        crosslinkmanager = CrosslinkManager()

        crosslink = ('001002002002', '001002')
        is_circular = crosslinkmanager.check_crosslink(crosslink)
        self.assertTrue(is_circular)

        crosslink_2 = ('001002002002', '001003')
        is_circular_2 = crosslinkmanager.check_crosslink(crosslink_2)
        self.assertFalse(is_circular_2)


    @test_settings
    def test_check_circularity_simple(self):

        crosslinkmanager = CrosslinkManager()

        crosslinks = [('001002002002', '001002'), ('001001003', '001002002')]
        is_circular = crosslinkmanager.check_circularity(crosslinks)
        self.assertTrue(is_circular)

        crosslinks_2 = [('001002002002', '001003'), ('001001003', '001002002')]
        is_circular_2 = crosslinkmanager.check_circularity(crosslinks_2)
        self.assertFalse(is_circular_2)

    
    @test_settings
    def test_check_circularity_complex(self):

        crosslinkmanager = CrosslinkManager()

        crosslinks = [('001002002002', '001003'), ('001001003', '001002002'), ('001003001', '001002002002001')]
        is_circular = crosslinkmanager.check_circularity(crosslinks)
        self.assertFalse(is_circular)

        crosslinks_2 = [('001002002002', '001003'), ('001003001', '001001'), ('001001003','001002002')]
        is_circular_2 = crosslinkmanager.check_circularity(crosslinks_2)
        self.assertTrue(is_circular_2)




class TestNatureGuidesCrosslinks(WithNatureGuide, TenantTestCase):

    @test_settings
    def test_save(self):

        nature_guide = self.create_nature_guide()
        nuidmanager = NuidManager()
        nature_guide_nuid = nuidmanager.decimal_to_nuid(nature_guide.id)

        parent_node = nature_guide.root_node
        
        node = self.create_node(parent_node, 'First')
        self.assertEqual(node.taxon_nuid, '{0}001001'.format(nature_guide_nuid))
        
        sibling = self.create_node(parent_node, 'Second')
        
        child = self.create_node(node, 'Child')
        self.assertEqual(child.taxon_nuid, '{0}001001001'.format(nature_guide_nuid))
        
        child_child = self.create_node(child, 'Child child')
        self.assertEqual(child_child.taxon_nuid, '{0}001001001001'.format(nature_guide_nuid))

        meta_node = child.meta_node
        cache_manager = ChildrenCacheManager(meta_node)
        cache_manager.add_or_update_child(child_child)

        crosslink = NatureGuideCrosslinks(
            parent=child,
            child=sibling,
        )

        crosslink.save()

        # test uplink circle
        crosslink_2 = NatureGuideCrosslinks(
            parent=child_child,
            child=node,
        )

        with self.assertRaises(ValueError):
            crosslink_2.save()

        meta_node.refresh_from_db()
        cache = meta_node.children_cache

        uuids_in_cache = [item['uuid'] for item in cache['items']]
        self.assertIn(str(sibling.name_uuid), uuids_in_cache)


    @test_settings
    def test_delete(self):

        nature_guide = self.create_nature_guide()
        nuidmanager = NuidManager()
        nature_guide_nuid = nuidmanager.decimal_to_nuid(nature_guide.id)

        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First')
        
        sibling = self.create_node(parent_node, 'Second')
        child = self.create_node(node, 'Child')
        child_child = self.create_node(child, 'Child child')

        meta_node = child.meta_node
        cache_manager = ChildrenCacheManager(meta_node)
        cache_manager.add_or_update_child(child_child)
    
        crosslink = NatureGuideCrosslinks(
            parent=child,
            child=sibling,
        )

        crosslink.save()

        meta_node.refresh_from_db()
        cache = meta_node.children_cache

        uuids_in_cache = [item['uuid'] for item in cache['items']]
        self.assertIn(str(sibling.name_uuid), uuids_in_cache)

        crosslink.delete()

        meta_node.refresh_from_db()
        cache = meta_node.children_cache

        uuids_in_cache = [item['uuid'] for item in cache['items']]
        self.assertFalse(str(sibling.name_uuid) in uuids_in_cache)
        

class TestMatrixFilter(WithNatureGuide, TenantTestCase):

    @test_settings
    def test_init(self):

        for filter_tuple in MATRIX_FILTER_TYPES:

            filter_type = filter_tuple[0]

            matrix_filter = MatrixFilter(
                filter_type=filter_type
            )

            self.assertTrue(matrix_filter.matrix_filter_type != None)

            self.assertEqual(matrix_filter.space_model, MatrixFilterSpace)

            if filter_type == 'ColorFilter':
                self.assertTrue(isinstance(matrix_filter.matrix_filter_type, ColorFilter))
                
            elif filter_type == 'RangeFilter':
                self.assertTrue(isinstance(matrix_filter.matrix_filter_type, RangeFilter))
                
            elif filter_type == 'NumberFilter':
                self.assertTrue(isinstance(matrix_filter.matrix_filter_type, NumberFilter))
                
            elif filter_type == 'DescriptiveTextAndImagesFilter':
                self.assertTrue(isinstance(matrix_filter.matrix_filter_type, DescriptiveTextAndImagesFilter))

            elif filter_type == 'TaxonFilter':
                self.assertTrue(isinstance(matrix_filter.matrix_filter_type, TaxonFilter))
            

    def perform_get_space_test(self, filter_type, encoded_space):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        
        node = self.create_node(parent_node, 'First')

        matrix_filter = MatrixFilter(
            meta_node = node.meta_node,
            name=filter_type,
            filter_type=filter_type,
        )

        matrix_filter.save()

        space = MatrixFilterSpace(
            matrix_filter=matrix_filter,
            encoded_space=encoded_space,
        )

        space.save()

        space_qry = matrix_filter.get_space()
        self.assertEqual(space_qry.count(), 1)
        self.assertEqual(space_qry[0], space)

        
    @test_settings
    def test_get_space_color(self):
        self.perform_get_space_test('ColorFilter', [255,255,255,0.1])

    @test_settings
    def test_get_space_range(self):
        self.perform_get_space_test('RangeFilter', [-3,3])

    @test_settings
    def test_get_space_number(self):
        self.perform_get_space_test('NumberFilter', [1,2,10,15])

    @test_settings
    def test_get_space_descriptivetextandimages(self):
        self.perform_get_space_test('DescriptiveTextAndImagesFilter', 'description')

    @test_settings
    def test_get_space_taxon(self):
        self.perform_get_space_test('TaxonFilter', self.get_taxonfilter_space())


    @test_settings
    def test_load_filter_type(self):

        with self.assertRaises(ValueError):

            matrix_filter = MatrixFilter()

    @test_settings
    def test_save(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First')

        meta_node = parent_node.meta_node
        cache_manager = ChildrenCacheManager(meta_node)
        cache_manager.add_or_update_child(node)

        filter_type = 'RangeFilter'

        meta_node.refresh_from_db()
        cache = meta_node.children_cache
        self.assertEqual(cache['matrix_filter_types'], {})

        matrix_filter = MatrixFilter(
            meta_node = meta_node,
            name=filter_type,
            filter_type=filter_type,
        )

        matrix_filter.save()

        meta_node.refresh_from_db()
        cache = meta_node.children_cache
        self.assertEqual(cache['matrix_filter_types'][str(matrix_filter.uuid)], filter_type)


    @test_settings
    def test_delete(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First')

        meta_node = parent_node.meta_node
        cache_manager = ChildrenCacheManager(meta_node)
        cache_manager.add_or_update_child(node)

        filter_type = 'RangeFilter'

        parent_node.meta_node.refresh_from_db()
        cache = parent_node.meta_node.children_cache
        self.assertEqual(cache['matrix_filter_types'], {})

        matrix_filter = MatrixFilter(
            meta_node = meta_node,
            name=filter_type,
            filter_type=filter_type,
        )

        matrix_filter.save()

        meta_node.refresh_from_db()
        cache = meta_node.children_cache
        self.assertEqual(cache['matrix_filter_types'][str(matrix_filter.uuid)], filter_type)

        matrix_filter.delete()

        meta_node.refresh_from_db()
        cache = meta_node.children_cache
        self.assertEqual(cache['matrix_filter_types'], {})


    @test_settings
    def test_str(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        
        node = self.create_node(parent_node, 'First')

        name = 'Test Filter'

        matrix_filter = MatrixFilter(
            meta_node=node.meta_node,
            name=name,
            filter_type='ColorFilter',
        )

        matrix_filter.save()

        self.assertEqual(str(matrix_filter), name)


class TestMatrixFilterSpace(WithNatureGuide, TenantTestCase):


    def perform_save_test(self, filter_type, working_space, breaking_space):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node

        matrix_filter = MatrixFilter(
            meta_node = parent_node.meta_node,
            name=filter_type,
            filter_type=filter_type,
        )

        matrix_filter.save()

        space = MatrixFilterSpace(
            matrix_filter=matrix_filter,
            encoded_space=working_space,
        )

        space.save()


        space_2 = MatrixFilterSpace(
            matrix_filter=matrix_filter,
            encoded_space=breaking_space,
        )

        with self.assertRaises(ValueError):
            space_2.save()

        return parent_node, space


    def perform_update_test(self, parent_node, space, new_value):

        matrix_filter_uuid = str(space.matrix_filter.uuid)

        # an item is needed
        node = self.create_node(parent_node, 'First')
        
        node_space = NodeFilterSpace(
            node=node,
            matrix_filter=space.matrix_filter,
        )
        node_space.save()
        node_space.values.add(space)

        cache = ChildrenCacheManager(parent_node.meta_node)
        cache.add_or_update_child(node)


        meta_node = space.matrix_filter.meta_node
        meta_node.refresh_from_db()
        item = meta_node.children_cache['items'][0]
        self.assertEqual(item['space'][str(matrix_filter_uuid)], [space.encoded_space])

        # test update
        old_value = space.encoded_space

        space.encoded_space = new_value
        space.save(old_encoded_space=old_value)

        meta_node.refresh_from_db()
        item = meta_node.children_cache['items'][0]
        self.assertEqual(item['space'][str(matrix_filter_uuid)], [new_value])


    def perform_deletion_test(self, parent_node, space):

        matrix_filter_uuid = str(space.matrix_filter.uuid)
        
        cache = parent_node.meta_node.children_cache
        item = cache['items'][0]

        self.assertEqual(item['space'][str(matrix_filter_uuid)], [space.encoded_space])

        encoded_space = space.encoded_space
        space.delete()
        self.assertFalse(encoded_space in item['space'][str(matrix_filter_uuid)])
        self.assertEqual(item['space'][str(matrix_filter_uuid)], [])
        

    @test_settings
    def test_save_color_filter(self):

        parent_node, space = self.perform_save_test('ColorFilter', [255,255,255,0.5], [255,'255',255,0.5])
        self.perform_update_test(parent_node, space, [111,222,333,1.0])

        self.perform_deletion_test(parent_node, space)
        

    @test_settings
    def test_save_range_filter(self):

        parent_node, space = self.perform_save_test('RangeFilter', [-5,5.5], [-5,'5.5'])

    
    @test_settings
    def test_save_number_filter(self):

        parent_node, space = self.perform_save_test('NumberFilter', [1,2,3,4,5,9], [1,2,3,'4',5,9])
            
    
    @test_settings
    def test_save_descriptivetexandimages_filter(self):

        parent_node, space = self.perform_save_test('DescriptiveTextAndImagesFilter', 'description', 1)

        self.perform_update_test(parent_node, space, 'New DTAI value')

        self.perform_deletion_test(parent_node, space)

    
    @test_settings
    def test_save_taxon_filter(self):

        taxonfilter = self.get_taxonfilter_space()

        filter_dict = taxonfilter[0].copy()
        del filter_dict['is_custom']
        taxonfilter_2 = [filter_dict]
        
        parent_node, space = self.perform_save_test('TaxonFilter', taxonfilter, taxonfilter_2)


    def perform_decode_test(self, filter_type, encoded_space, expected_decoded_space):
        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        
        node = self.create_node(parent_node, 'First')

        matrix_filter = MatrixFilter(
            meta_node = node.meta_node,
            name=filter_type,
            filter_type=filter_type,
        )

        matrix_filter.save()

        space = MatrixFilterSpace(
            matrix_filter=matrix_filter,
            encoded_space=encoded_space,
        )

        space.save()

        decoded_space = space.decode()

        self.assertEqual(decoded_space, expected_decoded_space)
        
            
    @test_settings
    def test_decode_color(self):

        self.perform_decode_test('ColorFilter', [255,123,10,0.1], 'rgba(255,123,10,0.1)')

    @test_settings
    def test_decode_range(self):
        # cant be decoded
        pass

    @test_settings
    def test_decode_number(self):
        # cant be decoded
        pass

    @test_settings
    def test_decode_descriptivetextandimages(self):
        # cant be decoded
        pass

    @test_settings
    def test_decode_taxon(self):
        # cant be decoded
        pass


    @test_settings
    def test_delete(self):
        pass
    

    @test_settings
    def test_str(self):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        
        node = self.create_node(parent_node, 'First')

        taxonfilter = self.get_taxonfilter_space()

        encoded_spaces = {
            'ColorFilter' : [0,0,0,1],
            'RangeFilter' : [4,7],
            'DescriptiveTextAndImagesFilter' : 'description',
            'NumberFilter' : [1,2,3,4],
            'TaxonFilter' : taxonfilter,
        }

        for filter_tuple in MATRIX_FILTER_TYPES:

            filter_type = filter_tuple[0]

            matrix_filter = MatrixFilter(
                meta_node = node.meta_node,
                name=filter_type,
                filter_type=filter_type,
            )

            matrix_filter.save()

            space = MatrixFilterSpace(
                matrix_filter=matrix_filter,
                encoded_space=encoded_spaces[filter_type],
            )

            space.save()

            self.assertEqual(str(space), str(matrix_filter.matrix_filter_type.verbose_space_name))
            

class TestNodeFilterSpace(WithNatureGuide, TenantTestCase):


    def create_matrix_filter_space(self, filter_type, encoded_space):

        nature_guide = self.create_nature_guide()

        parent_node = nature_guide.root_node
        
        node = self.create_node(parent_node, 'First')

        matrix_filter = MatrixFilter(
            meta_node = node.meta_node,
            name=filter_type,
            filter_type=filter_type,
        )

        matrix_filter.save()

        space = MatrixFilterSpace(
            matrix_filter=matrix_filter,
            encoded_space=encoded_space,
        )

        space.save()

        return node, matrix_filter, space


    def perform_save_test(self, node, matrix_filter, space, encoded_space=None, value=None):

        node_space = NodeFilterSpace(
            node=node,
            matrix_filter=matrix_filter,
        )

        if encoded_space:
            node_space.encoded_space=encoded_space


        node_space.save()

        if value:
            node_space.values.add(value)

        node_space_2 = NodeFilterSpace(
            node=node,
            matrix_filter=matrix_filter,
        )

        if not encoded_space:
            node_space_2.encoded_space=['json']

        with self.assertRaises(ValueError):
            node_space_2.save()


    @test_settings
    def test_save_color(self):

        node, matrix_filter, space = self.create_matrix_filter_space('ColorFilter', [123,456,101,0.5])

        self.perform_save_test(node, matrix_filter, space, encoded_space=None, value=space)
            

    @test_settings
    def test_save_range(self):

        node, matrix_filter, space = self.create_matrix_filter_space('RangeFilter', [1,4])

        self.perform_save_test(node, matrix_filter, space, encoded_space=[1,3], value=None)


    @test_settings
    def test_save_number(self):

        node, matrix_filter, space = self.create_matrix_filter_space('NumberFilter', [1,2,3,10])

        self.perform_save_test(node, matrix_filter, space, encoded_space=[1,2], value=None)
        

    @test_settings
    def test_save_descriptivetextandimages(self):

        node, matrix_filter, space = self.create_matrix_filter_space('DescriptiveTextAndImagesFilter', 'description')

        self.perform_save_test(node, matrix_filter, space, encoded_space=None, value=space)


    @test_settings
    def test_save_taxon(self):

        taxonfilter = self.get_taxonfilter_space()

        node, matrix_filter, space = self.create_matrix_filter_space('TaxonFilter', taxonfilter)

        self.perform_save_test(node, matrix_filter, space, encoded_space=None, value=space)



class TestChildrenCacheManager(WithNatureGuide, TenantTestCase):

    def get_encoded_spaces(self):

        taxonfilter = self.get_taxonfilter_space()

        encoded_spaces = {
            'ColorFilter' : [0,0,0,1],
            'RangeFilter' : [4,7],
            'DescriptiveTextAndImagesFilter' : 'description',
            'NumberFilter' : [1,2,3,4],
            'TaxonFilter' : taxonfilter,
        }

        return encoded_spaces


    def get_taxon(self):
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        return lacerta_agilis


    def create_node_space(self, matrix_filter, node, space):

        filter_type = matrix_filter.filter_type

        node_spaces = {
            'ColorFilter' : None, # None -> use value m2m
            'RangeFilter' : [5,6],
            'DescriptiveTextAndImagesFilter' :None,
            'NumberFilter' : [1,3],
        }

        node_space = NodeFilterSpace(
            node=node,
            matrix_filter=matrix_filter,
        )

        if filter_type in node_spaces and node_spaces[filter_type] != None:
            node_encoded_space = node_spaces[filter_type]
            node_space.encoded_space = node_encoded_space
            node_space.save()

        elif filter_type != 'TaxonFilter':
            node_space.save()
            value = space
            node_space.values.add(value)

        return node_space
    

    @test_settings
    def test_init(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First')

        children_cache_manager = ChildrenCacheManager(node.meta_node)

        self.assertEqual(children_cache_manager.meta_node, node.meta_node)
        

    @test_settings
    def test_get_data(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        node = self.create_node(parent_node, 'First')

        children_cache_manager = ChildrenCacheManager(meta_node)

        expected_data = {
            'items' : [],
            'matrix_filter_types' : {},
        }

        data = children_cache_manager.get_data()

        self.assertEqual(expected_data, data)
        

    @test_settings
    def test_child_as_json(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        node = self.create_node(parent_node, 'First')

        children_cache_manager = ChildrenCacheManager(meta_node)

        # test child with empty spaces, no taxon
        child_json = children_cache_manager.child_as_json(node)

        expected_json = {
            'id' : node.id,
            'meta_node_id' : node.meta_node.id,
            'node_type' : node.meta_node.node_type,
            'image_url' : node.meta_node.image_url(), 
            'uuid' : str(node.name_uuid),
            'space' : {},
            'is_visible' : True,
            'name' : node.meta_node.name,
            'decision_rule' : node.decision_rule,
            'taxon' : None,
        }

        self.assertEqual(expected_json, child_json)
        
        # test child with empty spaces, with taxon
        lazy_taxon = self.get_taxon()
        node.meta_node.set_taxon(lazy_taxon)
        node.save(parent_node)

        expected_json['taxon'] = {
            'taxon_source' : 'taxonomy.sources.col',
            'taxon_latname' : 'Lacerta agilis',
            'taxon_author' : lazy_taxon.taxon_author,
            'name_uuid' : str(lazy_taxon.name_uuid),
            'taxon_nuid' : lazy_taxon.taxon_nuid,
        }

        child_json_wtaxon = children_cache_manager.child_as_json(node)
        self.assertEqual(expected_json, child_json_wtaxon)

        # test child with all spaces
        encoded_spaces = self.get_encoded_spaces()

        expected_space = {}

        for filter_tuple in MATRIX_FILTER_TYPES:

            filter_type = filter_tuple[0]

            matrix_filter = MatrixFilter(
                meta_node = parent_node.meta_node,
                name=filter_type,
                filter_type=filter_type,
            )

            matrix_filter.save()

            space = MatrixFilterSpace(
                matrix_filter=matrix_filter,
                encoded_space=encoded_spaces[filter_type],
            )

            space.save()

            node_space = self.create_node_space(matrix_filter, node, space)
            # add a nodefilterspace

            if filter_type != 'TaxonFilter':
                matrix_filter_uuid = str(matrix_filter.uuid)
                matrix_filter_type = matrix_filter.matrix_filter_type
                expected_space[matrix_filter_uuid] = matrix_filter_type.get_node_filter_space_as_list(
                    node_space)
            

        # check if all keys/values exist in the json
        child_json_wspaces = children_cache_manager.child_as_json(node)
        for key, value in expected_json.items():

            if key != 'space':
                self.assertIn(key, child_json_wspaces)
                self.assertEqual(value, child_json_wspaces[key])

        # check the spaces
        self.assertEqual(expected_space, child_json_wspaces['space'])
        

    @test_settings
    def test_add_or_update_child(self):
        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        node = self.create_node(parent_node, 'First')

        children_cache_manager = ChildrenCacheManager(meta_node)

        self.assertEqual(meta_node.children_cache, None)

        children_cache_manager.add_or_update_child(node)
        parent_node.refresh_from_db()

        self.assertIn('items', meta_node.children_cache)
        self.assertIn('matrix_filter_types', meta_node.children_cache)
        self.assertEqual(len(meta_node.children_cache['items']), 1)

        # 'items' is a list - check if the child is not added twice
        children_cache_manager.add_or_update_child(node)
        parent_node.refresh_from_db()
        self.assertEqual(len(meta_node.children_cache['items']), 1)


    @test_settings
    def test_remove_child(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        node = self.create_node(parent_node, 'First')

        children_cache_manager = ChildrenCacheManager(meta_node)

        children_cache_manager.add_or_update_child(node)
        children_cache_manager.remove_child(node)
        
        self.assertIn('items', meta_node.children_cache)
        self.assertIn('matrix_filter_types', meta_node.children_cache)
        self.assertEqual(len(meta_node.children_cache['items']), 0)


    @test_settings
    def test_add_matrix_filter(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        node = self.create_node(parent_node, 'First')

        children_cache_manager = ChildrenCacheManager(meta_node)

        for filter_tuple in MATRIX_FILTER_TYPES:

            filter_type = filter_tuple[0]

            matrix_filter = MatrixFilter(
                meta_node = parent_node.meta_node,
                name=filter_type,
                filter_type=filter_type,
            )

            matrix_filter.uuid = uuid.uuid4()

            matrix_filter_uuid = str(matrix_filter.uuid)

            # do not save the matrix filter because this would add the filter to the cache already

            children_cache_manager.add_matrix_filter(matrix_filter)

            meta_node.refresh_from_db()
            self.assertIn(matrix_filter_uuid, meta_node.children_cache['matrix_filter_types'])
            self.assertEqual(meta_node.children_cache['matrix_filter_types'][matrix_filter_uuid], filter_type)


    @test_settings
    def test_remove_matrix_filter(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        node = self.create_node(parent_node, 'First')

        children_cache_manager = ChildrenCacheManager(meta_node)

        for filter_tuple in MATRIX_FILTER_TYPES:

            filter_type = filter_tuple[0]

            matrix_filter = MatrixFilter(
                meta_node = parent_node.meta_node,
                name=filter_type,
                filter_type=filter_type,
            )

            matrix_filter.save()

            matrix_filter_uuid = str(matrix_filter.uuid)

            meta_node.refresh_from_db()
            self.assertIn(matrix_filter_uuid, meta_node.children_cache['matrix_filter_types'])

            # remove
            children_cache_manager.remove_matrix_filter(matrix_filter)
            meta_node.refresh_from_db()
            self.assertFalse(matrix_filter_uuid in meta_node.children_cache['matrix_filter_types'])


    @test_settings
    def test_add_matrix_filter_space(self):

        pass


    @test_settings
    def test_update_matrix_filter_space(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        node = self.create_node(parent_node, 'First')

        encoded_spaces = self.get_encoded_spaces()

        children_cache_manager = ChildrenCacheManager(meta_node)

        for filter_tuple in MATRIX_FILTER_TYPES:

            filter_type = filter_tuple[0]

            matrix_filter = MatrixFilter(
                meta_node = parent_node.meta_node,
                name=filter_type,
                filter_type=filter_type,
            )

            matrix_filter.save()

            matrix_filter_uuid = str(matrix_filter.uuid)

            space = MatrixFilterSpace(
                matrix_filter=matrix_filter,
                encoded_space=encoded_spaces[filter_type],
            )

            space.save()

            # add some spaces
            node_space = self.create_node_space(matrix_filter, node, space)

            # normally triggered by a view
            
            children_cache_manager.add_or_update_child(node)

            meta_node.refresh_from_db()
            cache = meta_node.children_cache

            self.assertEqual(len(cache['items']), 1)
            
            item = cache['items'][0]

            if item['uuid'] == node.name_uuid:


                if filter_type == 'ColorFilter':
                    old_value = space.values().first()
                    
                    self.assertIn(old_value, item['space'][matrix_filter_uuid])
                    
                    new_value = [255,255,255,1]

                    cache.update_matrix_filter_space(matrix_filter_uuid, old_value, new_value)

                    meta_node.refresh_from_db()
                    cache = meta_node.children_cache
                    item = cache['items'][0]

                    self.assertFalse(old_value in item['space'][matrix_filter_uuid])
                    self.assertIn(new_value, item['space'][matrix_filter_uuid])


                elif filter_type == 'DescriptiveTextAndImagesFilter':
                    old_value = space.values().first()
                    
                    self.assertIn(old_value, item['space'][matrix_filter_uuid])
                    
                    new_value = 'New Value text'

                    cache.update_matrix_filter_space(matrix_filter_uuid, old_value, new_value)
                    
                    meta_node.refresh_from_db()
                    cache = meta_node.children_cache
                    item = cache['items'][0]

                    self.assertFalse(old_value in item['space'][matrix_filter_uuid])
                    self.assertIn(new_value, item['space'][matrix_filter_uuid])

                else:
                    self.assertIn(space.encoded_space, item['space'][matrix_filter_uuid])
                        

    @test_settings
    def test_remove_matrix_filter_space(self):

        nature_guide = self.create_nature_guide()
        parent_node = nature_guide.root_node
        meta_node = parent_node.meta_node
        node = self.create_node(parent_node, 'First')

        encoded_spaces = self.get_encoded_spaces()

        children_cache_manager = ChildrenCacheManager(meta_node)

        for filter_tuple in MATRIX_FILTER_TYPES:

            filter_type = filter_tuple[0]

            matrix_filter = MatrixFilter(
                meta_node = parent_node.meta_node,
                name=filter_type,
                filter_type=filter_type,
            )

            matrix_filter.save()

            matrix_filter_uuid = str(matrix_filter.uuid)

            space = MatrixFilterSpace(
                matrix_filter=matrix_filter,
                encoded_space=encoded_spaces[filter_type],
            )

            space.save()

            # add some spaces
            node_space = self.create_node_space(matrix_filter, node, space)

            # normally triggered by a view
            
            children_cache_manager.add_or_update_child(node)

            meta_node.refresh_from_db()
            cache = meta_node.children_cache

            self.assertEqual(len(cache['items']), 1)
            
            item = cache['items'][0]

            if item['uuid'] == node.name_uuid:


                if filter_type == 'ColorFilter':
                    old_value = space.values().first()
                    
                    self.assertIn(old_value, item['space'][matrix_filter_uuid])
                    
                    cache.remove_matrix_filter_space(space)

                    meta_node.refresh_from_db()
                    cache = meta_node.children_cache
                    item = cache['items'][0]

                    self.assertFalse(old_value in item['space'][matrix_filter_uuid])


                elif filter_type == 'DescriptiveTextAndImagesFilter':
                    old_value = space.values().first()
                    
                    self.assertIn(old_value, item['space'][matrix_filter_uuid])
                    
                    cache.remove_matrix_filter_space(space)
                    
                    meta_node.refresh_from_db()
                    cache = meta_node.children_cache
                    item = cache['items'][0]

                    self.assertFalse(old_value in item['space'][matrix_filter_uuid])

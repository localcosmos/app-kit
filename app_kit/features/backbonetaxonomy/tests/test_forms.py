from django.test import TestCase
from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.backbonetaxonomy.forms import (SearchTaxonomicBackboneForm, AddMultipleTaxaForm,
                                                     ManageFulltreeForm, SwapTaxonForm)

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy


class TestSearchTaxonomicBackboneForm(TenantTestCase):

    @test_settings
    def test_init(self):

        form = SearchTaxonomicBackboneForm(taxon_search_url='/')
        self.assertEqual(str(form.fields['taxon'].label), 'Search app taxa')


class TestAddMultipleTaxaForm(WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        form = AddMultipleTaxaForm()

        post_data = {
            'source' : 'taxonomy.sources.col',
            'taxa' : 'Lacerta agilis, Turdus merula, Something',
        }

        self.perform_form_test(AddMultipleTaxaForm, post_data)


class TestManageFulltreeForm(WithMetaApp, WithFormTest, TenantTestCase):

    @test_settings
    def test_init(self):

        form = ManageFulltreeForm()
        self.assertEqual(form.fields['include_full_tree'].initial, None)

        generic_content_link = self.get_generic_content_link(BackboneTaxonomy)
        generic_content = generic_content_link.generic_content
        generic_content.global_options = {
            'include_full_tree' : 'taxonomy.sources.col',
        }
        generic_content.save()
        
        form = ManageFulltreeForm(instance=generic_content)
        self.assertEqual(form.fields['include_full_tree'].initial, 'taxonomy.sources.col')
        
    
class TestSwapTaxonForm(WithMetaApp, WithFormTest, TenantTestCase):
    
    @test_settings
    def test_init(self):

        form = SwapTaxonForm()
        self.assertIn('from_taxon', form.fields)
        self.assertIn('to_taxon', form.fields)
from django.test import TestCase
from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.glossary.forms import GlossaryEntryForm, GlossaryEntryCategoryForm

from app_kit.features.glossary.tests.test_models import WithGlossary

class TestGlossaryEntryForm(WithFormTest, TenantTestCase):

    @test_settings
    def test_init(self):

        form = GlossaryEntryForm()

        post_data = {
            'id' : '1',
            'term' : 'Test term',
            'glossary' : '1',
            'definition' : 'Test definition',
            'synonyms' : 'synonym 1, synonym 2'
        }

        self.perform_form_test(GlossaryEntryForm, post_data)


class TestGlossaryEntryCategoryForm(WithGlossary, WithFormTest, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        self.glossary = self.create_glossary()

    @test_settings
    def test_init(self):

        form = GlossaryEntryCategoryForm(self.glossary)
        
        self.assertEqual(form.glossary, self.glossary)

        post_data = {
            'id' : '1',
            'name' : 'Test category',
        }

        self.perform_form_test(GlossaryEntryCategoryForm, post_data, form_args=(self.glossary,))
        
    @test_settings
    def test_name_uniqueness(self):

        category1 = self.create_glossary_entry_category(self.glossary, 'Test category')

        form_data = {
            'name' : 'Test category',
        }

        form = GlossaryEntryCategoryForm(self.glossary, data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
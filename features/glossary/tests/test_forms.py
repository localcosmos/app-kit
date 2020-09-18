from django.test import TestCase
from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.glossary.forms import GlossaryEntryForm




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



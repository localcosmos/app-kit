from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp,)

from app_kit.appbuilder.JSONBuilders.BackboneTaxonomyJSONBuilder import BackboneTaxonomyJSONBuilder, VernacularNames

from django.conf import settings


import os

BUFO_BUFO_VERNACULAR = {
    'taxonNuid': '006002009001005007001',
    'nameUuid': '1541aa08-7c23-4de0-9898-80d87e9227b3',
    'taxonSource': 'taxonomy.sources.col',
    'taxonLatname': 'Bufo bufo',
    'name': 'Erdkröte',
}

BUFO_BUFO_VERNACULAR_LONG = {
    'taxonNuid': '006002009001005007001',
    'nameUuid': '1541aa08-7c23-4de0-9898-80d87e9227b3',
    'taxonSource': 'taxonomy.sources.col',
    'taxonLatname': 'Bufo bufo',
    'name': 'Erdkrötenlaich',
}

class TestBackboneTaxonomyJSONBuilder(WithMetaApp, TenantTestCase):
    pass



class TestVernacularNames(WithMetaApp, TenantTestCase):

    @test_settings
    def test_add(self):

        vernacular_names = VernacularNames()

        vernacular_names.add(BUFO_BUFO_VERNACULAR, is_primary=True)
        vernacular_names.add(BUFO_BUFO_VERNACULAR_LONG, is_primary=True)

        name = vernacular_names.lookup[BUFO_BUFO_VERNACULAR['nameUuid']]
        self.assertEqual(name['primary'], 'Erdkröte')
        self.assertEqual(name['secondary'], ['Erdkrötenlaich'])

    @test_settings
    def test_replace_long_name(self):
        vernacular_names = VernacularNames()

        vernacular_names.add(BUFO_BUFO_VERNACULAR_LONG, is_primary=True)
        vernacular_names.add(BUFO_BUFO_VERNACULAR, is_primary=True)
        
        name = vernacular_names.lookup[BUFO_BUFO_VERNACULAR['nameUuid']]
        self.assertEqual(name['primary'], 'Erdkröte')
        self.assertEqual(name['secondary'], ['Erdkrötenlaich'])


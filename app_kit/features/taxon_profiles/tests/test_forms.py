from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django import forms
from django.conf import settings

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.taxon_profiles.forms import (TaxonProfilesOptionsForm, ManageTaxonTextTypeForm,
    ManageTaxonTextsForm, AddTaxonProfilesNavigationEntryTaxonForm, ManageTaxonTextTypeCategoryForm)

from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonTextType, TaxonProfile, TaxonText)

from app_kit.features.generic_forms.models import GenericForm

from app_kit.models import MetaAppGenericContent

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from .common import WithTaxonProfilesNavigation

import json


class TestTaxonProfilesOptionsForm(WithMetaApp, WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        generic_form = GenericForm.objects.create('Test form', self.meta_app.primary_language)
        form_link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(GenericForm),
            object_id=generic_form.id,
        )
        form_link.save()

        taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
        taxon_profiles = taxon_profiles_link.generic_content

        post_data = {
            'enable_wikipedia_button' : True,
            'enable_gbif_occurrence_map_button' : True,
            'enable_observation_button' : str(generic_form.uuid),
        }

        form_kwargs = {
            'meta_app' : self.meta_app,
            'generic_content' : taxon_profiles,
        }

        form = TaxonProfilesOptionsForm(**form_kwargs)

        self.perform_form_test(TaxonProfilesOptionsForm, post_data, form_kwargs=form_kwargs)


class TestManageTaxonTextTypeForm(WithMetaApp, WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
        taxon_profiles = taxon_profiles_link.generic_content
        
        post_data = {
            'text_type' : 'Test type',
            'taxon_profiles' : taxon_profiles.id,
        }

        form = ManageTaxonTextTypeForm()

        self.perform_form_test(ManageTaxonTextTypeForm, post_data)
    

class TestManageTaxonTextsForm(WithMetaApp, WithFormTest, TenantTestCase):


    def create_text_types(self, taxon_profiles):

        text_types = []

        for text_type_name in ['type_1', 'type_2']:

            text_type = TaxonTextType(
                taxon_profiles=taxon_profiles,
                text_type=text_type_name,
            )

            text_type.save()

            text_types.append(text_type)

        return text_types


    def create_taxon_profile(self, taxon_profiles):

        models = TaxonomyModelRouter('taxonomy.sources.col')

        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)
        
        taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=lazy_taxon,
        )

        taxon_profile.save()

        return taxon_profile

    @test_settings
    def test_init(self):

        taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
        taxon_profiles = taxon_profiles_link.generic_content

        text_types = self.create_text_types(taxon_profiles)

        # init without taxon profile
        form = ManageTaxonTextsForm(taxon_profiles)

        for text_type in text_types:
            self.assertIn(text_type.text_type, form.fields)
            self.assertIn(text_type.text_type, form.localizeable_fields)

        
        taxon_profile = self.create_taxon_profile(taxon_profiles)
        
        form = ManageTaxonTextsForm(taxon_profiles, taxon_profile=taxon_profile)

        for text_type in text_types:
            self.assertIn(text_type.text_type, form.fields)
            self.assertIn(text_type.text_type, form.localizeable_fields)

        # with texts
        for text_type in text_types:

            taxon_text = TaxonText(
                taxon_profile=taxon_profile,
                taxon_text_type=text_type,
                text='{0} {1}'.format(text_type.text_type, taxon_profile.taxon_latname),
                long_text='{0} {1} long'.format(text_type.text_type, taxon_profile.taxon_latname),
            )

            taxon_text.save()

        form = ManageTaxonTextsForm(taxon_profiles, taxon_profile=taxon_profile)

        for text_type in text_types:
            long_text_field_name = '{0}:longtext'.format(text_type.text_type)

            self.assertIn(text_type.text_type, form.short_text_fields)
            self.assertIn(text_type.text_type, form.fields)
            
            if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
                self.assertIn(long_text_field_name, form.fields)

            self.assertIn(text_type.text_type, form.localizeable_fields)
            if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
                self.assertIn(long_text_field_name, form.localizeable_fields)
                self.assertIn(long_text_field_name, form.long_text_fields)

            expected_initial = TaxonText.objects.get(taxon_profile=taxon_profile, taxon_text_type=text_type)
            self.assertEqual(form.fields[text_type.text_type].initial, expected_initial.text)
            
            if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
                self.assertEqual(form.fields[long_text_field_name].initial, expected_initial.long_text)



class TestAddTaxonProfilesNavigationEntryTaxonForm(WithTaxonProfilesNavigation, WithMetaApp, TenantTestCase):
    
    @test_settings
    def test_init(self):
        
        form = AddTaxonProfilesNavigationEntryTaxonForm(taxon_search_url='/test/')
        
        self.assertEqual(form.navigation_entry, None)
        self.assertEqual(form.parent, None)
        
        navigation_entry = self.create_navigation_entry()
        
        child_entry = self.create_navigation_entry(parent=navigation_entry)
        
        form2 = AddTaxonProfilesNavigationEntryTaxonForm(taxon_search_url='',navigation_entry=child_entry,
                                                         parent=navigation_entry)
        
        self.assertEqual(form2.parent, navigation_entry)
        self.assertEqual(form2.navigation_entry, child_entry)
    
    
    @test_settings
    def test_clean(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        animalia_db = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        animalia = LazyTaxon(instance=animalia_db)
        
        # add simple taxon
        post_data = {}
        
        animalia_post_data = self.taxon_to_post_data(animalia)
        post_data.update(animalia_post_data)
        
        form = AddTaxonProfilesNavigationEntryTaxonForm(data=post_data, taxon_search_url='/test/')
        
        form.is_valid()
        self.assertEqual(form.errors, {})
    
    @test_settings
    def test_clean_below_genus(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
        
        post_data = {}
        
        lacerta_agilis_post_data = self.taxon_to_post_data(lacerta_agilis)
        post_data.update(lacerta_agilis_post_data)
        
        form = AddTaxonProfilesNavigationEntryTaxonForm(data=post_data, taxon_search_url='/test/')
        
        form.is_valid()
        self.assertIn('taxon', form.errors)
        
        self.assertIn('below genus', form.errors['taxon'][0])
    
    
    @test_settings
    def test_clean_already_exists(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        animalia_db = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        animalia = LazyTaxon(instance=animalia_db)
        
        navigation_entry = self.create_navigation_entry(taxon=animalia)
        
        taxa_names = navigation_entry.taxa.values_list('name_uuid', flat=True)
        taxa_names_str = [str(t) for t in taxa_names]
        self.assertIn(animalia.name_uuid, taxa_names_str)
        
        post_data = {}
        
        animalia_post_data = self.taxon_to_post_data(animalia)
        post_data.update(animalia_post_data)
        
        form = AddTaxonProfilesNavigationEntryTaxonForm(data=post_data, taxon_search_url='/test/')
        
        form.is_valid()
        
        self.assertIn('taxon', form.errors)
        
        self.assertIn('already exists', form.errors['taxon'][0])
    
    @test_settings
    def test_clean_wrong_descendant(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        plantae_db = models.TaxonTreeModel.objects.get(taxon_latname='Plantae')
        plantae = LazyTaxon(instance=plantae_db)
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        chordata = LazyTaxon(instance=chordata_db)
        
        navigation_entry = self.create_navigation_entry(taxon=plantae)
        
        post_data = {}
        
        chordata_post_data = self.taxon_to_post_data(chordata)
        post_data.update(chordata_post_data)
        
        form = AddTaxonProfilesNavigationEntryTaxonForm(data=post_data, parent=navigation_entry,
                                                        taxon_search_url='/test/')
        
        form.is_valid()
        
        self.assertIn('taxon', form.errors)
        
        self.assertIn('not a valid descendant', form.errors['taxon'][0])
        
        
    @test_settings
    def test_clean_wrong_ascendant(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        navigation_entry = self.create_navigation_entry()
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        chordata = LazyTaxon(instance=chordata_db)
        
        child_entry = self.create_navigation_entry(parent=navigation_entry, taxon=chordata)
        
        plantae_db = models.TaxonTreeModel.objects.get(taxon_latname='Plantae')
        plantae = LazyTaxon(instance=plantae_db)
        
        post_data = {}
        
        plantae_post_data = self.taxon_to_post_data(plantae)
        post_data.update(plantae_post_data)
        
        form = AddTaxonProfilesNavigationEntryTaxonForm(data=post_data, navigation_entry=navigation_entry,
                                                        taxon_search_url='/test/')
        
        form.is_valid()
        
        self.assertIn('taxon', form.errors)
        
        self.assertIn('not a valid parent', form.errors['taxon'][0])
        
    @test_settings
    def test_clean_custom_wildcard(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        navigation_entry = self.create_navigation_entry()
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        chordata = LazyTaxon(instance=chordata_db)
        
        child_entry = self.create_navigation_entry(parent=navigation_entry, taxon=chordata)
        
        plantae_db = models.TaxonTreeModel.objects.get(taxon_latname='Plantae')
        plantae = LazyTaxon(instance=plantae_db)
        
        post_data = {}
        
        plantae_post_data = self.taxon_to_post_data(plantae)
        plantae_post_data.update({
            'taxon_0': 'taxonomy.sources.custom'
        })
        post_data.update(plantae_post_data)
        
        form = AddTaxonProfilesNavigationEntryTaxonForm(data=post_data, navigation_entry=navigation_entry,
                                                        taxon_search_url='/test/')
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        
class TestManageTaxonTextTypeCategoryForm(WithMetaApp, WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
        taxon_profiles = taxon_profiles_link.generic_content
        
        post_data = {
            'name' : 'Test type',
            'taxon_profiles' : taxon_profiles.id,
        }

        form = ManageTaxonTextTypeCategoryForm()

        self.perform_form_test(ManageTaxonTextTypeCategoryForm, post_data)
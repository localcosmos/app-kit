from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django import forms
from django.conf import settings

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.taxon_profiles.forms import (TaxonProfilesOptionsForm, ManageTaxonTextTypeForm,
    ManageTaxonTextsForm, AddTaxonProfilesNavigationEntryTaxonForm, ManageTaxonTextTypeCategoryForm,
    ManageTaxonTextSetForm, SetTaxonTextSetForTaxonProfileForm, CreateTaxonProfileForm)

from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonTextType, TaxonProfile, TaxonText,
                                                    TaxonTextSet)

from app_kit.features.object_classes.models import ObjectClasses, ObjectClass, ObjectClassTaxon

from app_kit.models import MetaAppGenericContent

from app_kit.features.generic_forms.models import GenericForm

from app_kit.models import MetaAppGenericContent

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from .common import WithTaxonProfilesNavigation

from .common import WithTaxonProfilesNavigation


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

        form = ManageTaxonTextTypeForm(taxon_profiles)

        self.perform_form_test(ManageTaxonTextTypeForm, post_data, form_args=[taxon_profiles])
    

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
        

        # init without taxon profile - why?
        #form = ManageTaxonTextsForm(taxon_profiles, taxon_profile)

        #for text_type in text_types:
        #    self.assertIn(text_type.text_type, form.fields)
        #    self.assertIn(text_type.text_type, form.localizeable_fields)

        
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
        
        
class TestManageTaxonTextSetForm(WithMetaApp, WithFormTest, TenantTestCase):
    
    @test_settings
    def test_init(self):

        taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
        taxon_profiles = taxon_profiles_link.generic_content
        
        text_type = TaxonTextType(
            taxon_profiles=taxon_profiles,
            text_type='Test text type',
        )
        text_type.save()
        
        text_set_form = ManageTaxonTextSetForm(taxon_profiles)

        self.assertIn('name', text_set_form.fields)
        self.assertIn('taxon_profiles', text_set_form.fields)
        self.assertIn('text_types', text_set_form.fields)

        self.assertEqual(text_set_form.fields['text_types'].queryset.count(), 1)

    @test_settings
    def test_form(self):

        taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
        taxon_profiles = taxon_profiles_link.generic_content
        
        text_type = TaxonTextType(
            taxon_profiles=taxon_profiles,
            text_type='Test text type',
        )
        text_type.save()

        post_data = {
            'name' : 'Test set',
            'taxon_profiles' : taxon_profiles.id,
        }

        form = ManageTaxonTextSetForm(taxon_profiles)

        self.perform_form_test(ManageTaxonTextSetForm, post_data, form_args=[taxon_profiles])
        
        # post with text type
        post_data['text_types'] = [text_type.id]
        form = ManageTaxonTextSetForm(taxon_profiles)
        self.perform_form_test(ManageTaxonTextSetForm, post_data, form_args=[taxon_profiles])
        
        
    class TestSetTaxonTextSetForTaxonProfileForm(WithMetaApp, WithFormTest, TenantTestCase):
    
        @test_settings
        def test_init(self):

            taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
            taxon_profiles = taxon_profiles_link.generic_content
            
            text_type = TaxonTextType(
                taxon_profiles=taxon_profiles,
                text_type='Test text type',
            )
            text_type.save()

            text_set_form = SetTaxonTextSetForTaxonProfileForm(taxon_profiles)

            self.assertIn('text_set', text_set_form.fields)
            self.assertEqual(text_set_form.fields['text_set'].queryset.count(), 1)
    
        @test_settings
        def test_form(self):

            taxon_profiles_link = self.get_generic_content_link(TaxonProfiles)
            taxon_profiles = taxon_profiles_link.generic_content

            text_type = TaxonTextType(
                taxon_profiles=taxon_profiles,
                text_type='Test text type',
            )
            text_type.save()
            
            text_set = TaxonTextSet(
                taxon_profiles=taxon_profiles,
                name='Test set',
            )
            text_set.save()
            text_set.text_types.add(text_type)

            text_set_form = SetTaxonTextSetForTaxonProfileForm(taxon_profiles)

            self.assertIn('text_set', text_set_form.fields)
            self.assertEqual(text_set_form.fields['text_set'].queryset.count(), 1)
            
            post_data = {
                'text_set' : text_set.id,
            }
            
            form = SetTaxonTextSetForTaxonProfileForm(taxon_profiles)
            
            self.perform_form_test(SetTaxonTextSetForTaxonProfileForm, post_data, form_args=[taxon_profiles])


class TestCreateTaxonProfileForm(WithMetaApp, TenantTestCase):

    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)

    def taxon_to_post_data(self, taxon):
        return {
            'taxon_0': taxon.taxon_source,
            'taxon_1': taxon.taxon_latname,
            'taxon_2': taxon.taxon_author,
            'taxon_3': str(taxon.name_uuid),
            'taxon_4': taxon.taxon_nuid,
        }

    def create_object_classes_with_link(self):
        object_classes = ObjectClasses.objects.create('Test Object Classes', self.meta_app.primary_language)
        link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(ObjectClasses),
            object_id=object_classes.id,
        )
        link.save()
        return object_classes

    @test_settings
    def test_init_without_object_classes(self):
        form = CreateTaxonProfileForm(self.meta_app, language=self.meta_app.primary_language)
        self.assertIn('taxon', form.fields)
        self.assertIn('morphotype', form.fields)
        self.assertIn('object_class', form.fields)
        # no ObjectClasses linked to the meta_app, queryset should be empty
        self.assertEqual(form.fields['object_class'].queryset.count(), 0)

    @test_settings
    def test_init_with_object_classes(self):
        object_classes = self.create_object_classes_with_link()
        ObjectClass.objects.create(
            object_classes=object_classes,
            name='Test Class',
            scientific_name='test_class',
        )

        form = CreateTaxonProfileForm(self.meta_app, language=self.meta_app.primary_language)
        self.assertEqual(form.fields['object_class'].queryset.count(), 1)

    @test_settings
    def test_form_valid_taxon_only(self):
        post_data = {
            'input_language': self.meta_app.primary_language,
        }
        post_data.update(self.taxon_to_post_data(self.lazy_taxon))

        form = CreateTaxonProfileForm(self.meta_app, data=post_data, language=self.meta_app.primary_language)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})
        self.assertTrue(is_valid)
        self.assertEqual(form.cleaned_data['taxon'], self.lazy_taxon)

    @test_settings
    def test_form_valid_with_morphotype(self):
        post_data = {
            'input_language': self.meta_app.primary_language,
            'morphotype': 'Imago',
        }
        post_data.update(self.taxon_to_post_data(self.lazy_taxon))

        form = CreateTaxonProfileForm(self.meta_app, data=post_data, language=self.meta_app.primary_language)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})
        self.assertTrue(is_valid)
        self.assertEqual(form.cleaned_data['morphotype'], 'Imago')

    @test_settings
    def test_form_valid_with_valid_object_class(self):
        object_classes = self.create_object_classes_with_link()
        object_class = ObjectClass.objects.create(
            object_classes=object_classes,
            name='Test Class',
            scientific_name='test_class',
        )
        # Link the taxon to the object class so the combination is valid
        taxon_link = ObjectClassTaxon(object_class=object_class)
        taxon_link.set_taxon(self.lazy_taxon)
        taxon_link.save()

        post_data = {
            'input_language': self.meta_app.primary_language,
            'object_class': object_class.id,
        }
        post_data.update(self.taxon_to_post_data(self.lazy_taxon))

        form = CreateTaxonProfileForm(self.meta_app, data=post_data, language=self.meta_app.primary_language)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})
        self.assertTrue(is_valid)

    @test_settings
    def test_clean_invalid_object_class(self):
        object_classes = self.create_object_classes_with_link()
        object_class = ObjectClass.objects.create(
            object_classes=object_classes,
            name='Test Class',
            scientific_name='test_class',
        )
        # Link the object class to a different taxon (Plantae), not to self.lazy_taxon
        models = TaxonomyModelRouter('taxonomy.sources.col')
        plantae_db = models.TaxonTreeModel.objects.get(taxon_latname='Plantae')
        plantae = LazyTaxon(instance=plantae_db)

        taxon_link = ObjectClassTaxon(object_class=object_class)
        taxon_link.set_taxon(plantae)
        taxon_link.save()

        post_data = {
            'input_language': self.meta_app.primary_language,
            'object_class': object_class.id,
        }
        post_data.update(self.taxon_to_post_data(self.lazy_taxon))

        form = CreateTaxonProfileForm(self.meta_app, data=post_data, language=self.meta_app.primary_language)
        is_valid = form.is_valid()
        self.assertFalse(is_valid)
        self.assertIn('object_class', form.errors)
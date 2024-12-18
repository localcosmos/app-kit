from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, WithFormTest, WithZipFile, WithImageStore, WithMedia, WithUser,
                                  WithPublicDomain, WithMetaVernacularNames)

from app_kit.forms import (CleanAppSubdomainMixin, CreateAppForm, CreateGenericContentForm, AddLanguageForm,
                    ManageContentImageForm, ManageContentImageWithTextForm, OptionalContentImageForm,
                    GenericContentOptionsForm, EditGenericContentNameForm, MetaAppOptionsForm,
                    TranslateAppForm, BuildAppForm, ZipImportForm, RESERVED_SUBDOMAINS, AddExistingGenericContentForm,
                    TranslateVernacularNamesForm)

from app_kit.multi_tenancy.models import Domain
from app_kit.models import (MetaAppGenericContent, ContentImage, LocalizedContentImage)

from app_kit.tests.common import (TEST_MEDIA_ROOT, TEST_IMAGE_PATH)

from taxonomy.lazy import TaxonomyModelRouter, LazyTaxon
from taxonomy.models import MetaVernacularNames

from django.conf import settings

import uuid, json, hashlib, base64, os


class TestCleanAppSubdomainMixin(WithMetaApp, TenantTestCase):

    def get_mixin_with_value(self, value):

        mixin = CleanAppSubdomainMixin()
        mixin.cleaned_data = {
            'subdomain' : value,
        }

        return mixin

    @test_settings
    def test_wrong_encoding(self):

        value = 'Á É Í Ó Ú Ý Ć Ǵ Ḱ Ĺ Ḿ Ń Ṕ Ŕ Ś Ẃ Ź'

        with self.assertRaises(UnicodeEncodeError):
            value.encode('ascii')
            
        mixin = self.get_mixin_with_value(value)

        with self.assertRaises(forms.ValidationError):
            subdomain = mixin.clean_subdomain()
        
    @test_settings
    def test_in_reserved(self):

        value = RESERVED_SUBDOMAINS[0]
        mixin = self.get_mixin_with_value(value)

        with self.assertRaises(forms.ValidationError):
            subdomain = mixin.clean_subdomain()

    @test_settings
    def test_0_unalpha(self):
        value = '1test'

        mixin = self.get_mixin_with_value(value)

        with self.assertRaises(forms.ValidationError):
            subdomain = mixin.clean_subdomain()

    @test_settings
    def test_is_not_alphanumeric(self):

        value = 'test!'

        mixin = self.get_mixin_with_value(value)

        with self.assertRaises(forms.ValidationError):
            subdomain = mixin.clean_subdomain()
            
    @test_settings
    def test_already_exists(self):

        domain = Domain(
            domain='test.lc.org',
            tenant=self.tenant,
            app=self.meta_app.app,
        )

        domain.save()

        value = 'test'

        mixin = self.get_mixin_with_value(value)

        with self.assertRaises(forms.ValidationError):
            subdomain = mixin.clean_subdomain()

    @test_settings
    def test_valid(self):

        value = 'test2'
        mixin = self.get_mixin_with_value(value)
        subdomain = mixin.clean_subdomain()
        self.assertEqual(subdomain, value)



class TestCreateAppForm(WithFormTest, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):
        form = CreateAppForm()

        frontend_field = form.fields['frontend']
        
        choices = [c[0] for c in frontend_field.choices]

        self.assertIn(settings.APP_KIT_DEFAULT_FRONTEND, choices)

    @test_settings
    def test_form_no_uuid(self):

        post_data = {
            'name' : 'My Great App',
            'primary_language' : 'en',
            'subdomain' : 'subdomain',
            'frontend' : 'Multiverse',
        }

        
        self.perform_form_test(CreateAppForm, post_data)

        
    @test_settings
    def test_form_with_uuid(self):

        post_data = {
            'name' : 'My Great App',
            'primary_language' : 'en',
            'subdomain' : 'subdomain',
            'uuid' : str(uuid.uuid4()),
        }

        form_kwargs = {
            'allow_uuid' : True,
        }

        
        self.perform_form_test(CreateAppForm, post_data, form_kwargs=form_kwargs)


    @test_settings
    def test_clean_name(self):

        app_name = 'My great app'

        form =CreateAppForm()
        form.cleaned_data = {'name': app_name}

        cleaned_name = form.clean_name()
        self.assertEqual(app_name, cleaned_name)

        form.cleaned_data = {'name':self.meta_app.app.name}
        with self.assertRaises(forms.ValidationError):
            cleaned_name = form.clean_name()


class TestCreateGenericContentForm(WithFormTest, TestCase):

    @test_settings
    def test_form(self):
        post_data = {
            'name' : 'My Great Content',
            'input_language' : 'en',
            'content_type_id' : 1,
        }
        
        self.perform_form_test(CreateGenericContentForm, post_data)
        

class TestAddLanguageForm(WithFormTest, TestCase):

    @test_settings
    def test_form(self):
        post_data = {
            'language' : 'en',
        }

        
        self.perform_form_test(AddLanguageForm, post_data)


# respect licencingformmixin
# derives from ManageContentImageFormCommon
class TestManageContentImageForm(WithFormTest, TestCase):


    @test_settings
    def test_form(self):

        licencing_data = self.get_licencing_post_data()

        image = self.get_image('test-image.jpg')
        correct_md5 = hashlib.md5(image.read()).hexdigest()

        crop_parameters = {
            'width' : 12,
            'height' : 20,
        }
        
        post_data = {
            'crop_parameters' : json.dumps(crop_parameters),
            'image_type' : 'image',
            'md5' : correct_md5,
        }

        file_dict = {
            'source_image' : self.get_image,
        }

        post_data.update(licencing_data)

        # add source_image to requirement, otherwise form.current_image woudl have to be set
        self.perform_form_test(ManageContentImageForm, post_data, file_data=file_dict,
                               required_fields=['source_image'])


    @test_settings
    def test_clean_source_image(self):

        form = ManageContentImageForm()
        form.cleaned_data = {}

        with self.assertRaises(forms.ValidationError):
            source_image = form.clean_source_image()

        image = self.get_image('test-image.jpg')
        form.current_image = image

        source_image = form.clean_source_image()
        self.assertEqual(source_image, None)

        form.current_image = None
        form.cleaned_data = {
            'source_image' : image,
        }

        source_image = form.clean_source_image()
        self.assertEqual(source_image, image)


class TestManageContentImageWithTextForm(WithFormTest, TestCase):

    @test_settings
    def test_form(self):

        licencing_data = self.get_licencing_post_data()

        image = self.get_image('test-image.jpg')
        correct_md5 = hashlib.md5(image.read()).hexdigest()

        crop_parameters = {
            'width' : 12,
            'height' : 20,
        }
        
        post_data = {
            'text' : 'Text for a beautiful image',
            'crop_parameters' : json.dumps(crop_parameters),
            'image_type' : 'image',
            'md5' : correct_md5,
        }

        file_dict = {
            'source_image' : self.get_image,
        }

        post_data.update(licencing_data)

        # add source_image to requirement, otherwise form.current_image woudl have to be set
        self.perform_form_test(ManageContentImageForm, post_data, file_data=file_dict,
                               required_fields=['source_image'])
    


class TestOptionalContentImageForm(WithFormTest, TestCase):

    @test_settings
    def test_fields_required(self):
        post_data = {
            'image_type' : 'image',
        }
        form = OptionalContentImageForm(post_data)
        form.cleaned_data = {}
        form._clean_fields()

        form.fields_required(['image_type'])
        self.assertEqual(form._errors, None)
        
        form.fields_required(['crop_parameters'])
        self.assertTrue('crop_parameters' in form._errors)
        

    @test_settings
    def test_clean(self):

        licencing_data = self.get_licencing_post_data()

        crop_parameters = {
            'width' : 12,
            'height' : 20,
        }

        post_data = {
            'image_type' : 'image',
            'crop_parameters' : json.dumps(crop_parameters),
        }

        post_data.update(licencing_data)
        
        form = OptionalContentImageForm(post_data)
        form.cleaned_data = {}
        form._clean_fields()

        # no error
        cleaned_data = form.clean()

        # file, but no creator name
        image = self.get_image()
        correct_md5 = hashlib.md5(image.read()).hexdigest()

        file_dict = {
            'source_image' : self.get_image(),
        }

        post_data_2 = {
            'image_type' : 'image',
            'crop_parameters' : json.dumps(crop_parameters),
        }

        post_data_2.update(licencing_data)
        del post_data_2['creator_name']


        form_2 = OptionalContentImageForm(data=post_data_2, files=file_dict)
        form_2.cleaned_data = {}
        form_2._clean_fields()
        
        cleaned_data = form_2.clean()
        self.assertTrue('creator_name' in form_2._errors)

        # file, but no licence
        file_dict_2 = {
            'source_image' : self.get_image(),
        }

        post_data_3 = {
            'image_type' : 'image',
            'crop_parameters' : json.dumps(crop_parameters),
        }

        post_data_3.update(licencing_data)
        del post_data_3['licence_0']


        form_3 = OptionalContentImageForm(data=post_data_3, files=file_dict_2)
        form_3.cleaned_data = {}
        form_3._clean_fields()

        cleaned_data = form_3.clean()
        self.assertTrue('licence' in form_3._errors)
    


class TestGenericContentOptionsForm(WithFormTest, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):

        self.create_all_generic_contents(self.meta_app)

        generic_content_link = MetaAppGenericContent.objects.filter(meta_app=self.meta_app).first()
        generic_content = generic_content_link.generic_content

        with self.assertRaises(KeyError):
            form = GenericContentOptionsForm()

        form_kwargs = {
            'generic_content' : generic_content,
        }

        with self.assertRaises(KeyError):
            form = GenericContentOptionsForm(**form_kwargs)

        form_kwargs = {
            'meta_app' : self.meta_app,
        }

        with self.assertRaises(KeyError):
            form = GenericContentOptionsForm(**form_kwargs)


        form_kwargs = {
            'meta_app' : self.meta_app,
            'generic_content' : generic_content,
        }

        form = GenericContentOptionsForm(**form_kwargs)
        self.assertEqual(form.meta_app, self.meta_app)
        self.assertEqual(form.generic_content, generic_content)
        self.assertEqual(form.primary_language, self.meta_app.primary_language)
        self.assertEqual(form.uuid_to_instance, {})
        self.assertEqual(form.initial, {})

        # add some options, no instance fields
        global_options = {
            'test global option' : 'tgp value',
        }
        generic_content.global_options = global_options
        generic_content.save()

        options = {
            'test option' : 'to value',
        }
        generic_content_link.options = options
        generic_content_link.save()

        form = GenericContentOptionsForm(**form_kwargs)

        for key, value in global_options.items():
            self.assertEqual(form.initial[key], value)

        for key, value in options.items():
            self.assertEqual(form.initial[key], value)


        # add some instance fields
        instance_option = self.meta_app.make_option_from_instance(generic_content)

        global_options = {
            'test global option' : instance_option,
        }
        generic_content.global_options = global_options
        generic_content.save()

        options = {
            'test option' : instance_option,
        }
        generic_content_link.options = options
        generic_content_link.save()

        GenericContentOptionsForm.instance_fields = ['test global option', 'test option']
        
        form = GenericContentOptionsForm(**form_kwargs)

        for key, value in global_options.items():
            self.assertEqual(form.initial[key], instance_option['uuid'])

        for key, value in options.items():
            self.assertEqual(form.initial[key], instance_option['uuid'])


        # reset Class
        GenericContentOptionsForm.instance_fields = []

        
class TestEditGenericContentNameForm(WithFormTest, WithMetaApp, TenantTestCase):

    @test_settings
    def test_form(self):

        post_data = {
            'content_type_id' : 1,
            'generic_content_id' : 2,
            'name' : 'Test Name',
            'input_language' : 'en',
        }

        self.perform_form_test(EditGenericContentNameForm, post_data)


class TestAddExistingGenericContentForm(WithFormTest, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):

        self.create_all_generic_contents(self.meta_app)

        generic_content_link = MetaAppGenericContent.objects.filter(meta_app=self.meta_app).first()
        generic_content = generic_content_link.generic_content
        content_type = generic_content_link.content_type
        
        form = AddExistingGenericContentForm(self.meta_app, content_type)
        self.assertEqual(len(form.fields['generic_content'].choices), 0)
        self.assertFalse(form.has_choices)


        generic_content_link_2 = MetaAppGenericContent.objects.filter(meta_app=self.meta_app).last()
        generic_content_2 = generic_content_link_2.generic_content
        content_type_2 = generic_content_link_2.content_type

        generic_content_link_2.delete()

        form_2 = AddExistingGenericContentForm(self.meta_app, content_type_2)
        self.assertEqual(len(form_2.fields['generic_content'].choices), 1)

        for choice, label in form_2.fields['generic_content'].choices:
            self.assertEqual(choice, generic_content_2.pk)
        


class TestMetaAppOptionsForm(WithFormTest, WithMetaApp, TenantTestCase):

    @test_settings
    def test_form(self):

        post_data = {
            'allow_anonymous_observations' : True,
            'localcosmos_private' : True,
            'localcosmos_private_api_url' : 'https://private.localcosmos.org',
        }

        form_kwargs = {
            'meta_app' : self.meta_app,
            'generic_content' : self.meta_app,
        }

        self.perform_form_test(MetaAppOptionsForm, post_data, form_kwargs=form_kwargs)


'''
    Test TranslateAppForm
    - secondary languages are needed
    - test if empty translations appear on top
'''
class TestTranslateAppForm(WithImageStore, WithMedia, WithFormTest, WithMetaApp, WithUser, WithPublicDomain,
                           TenantTestCase):


    def setUp(self):
        super().setUp()
        self.create_public_domain()


    def create_locale_entries(self, count=10):

        locale_entries = {}

        for c in range(0, count):

            key = 'key {0}'.format(c)
            value = 'value {0}'.format(c)

            locale_entries[key] = value

        
        if not self.meta_app.localizations:
            self.meta_app.localizations = {}
        self.meta_app.localizations[self.meta_app.primary_language] = locale_entries
        self.meta_app.save()

        return locale_entries


    def create_content_image(self):

        image_store = self.create_image_store()

        content_type = ContentType.objects.get_for_model(self.meta_app)

        content_image = ContentImage(
            image_store=image_store,
            content_type=content_type,
            object_id=self.meta_app.id,
        )

        content_image.save()

        return content_image
    

    @test_settings
    def test_init(self):

        languages = ['de', 'fr']

        self.create_secondary_languages(languages)

        locale_entries = self.create_locale_entries()

        form = TranslateAppForm(self.meta_app)
        self.assertEqual(form.meta_app, self.meta_app)
        self.assertEqual(form.page, 1)

        # check form fields
        for language in languages:

            for key, value in locale_entries.items():

                field_key = '{0}-{1}'.format(language, key)
                field_key_b64 = base64.b64encode(field_key.encode()).decode()
                self.assertIn(field_key_b64, form.fields)

                form_field = form.fields[field_key_b64]
                self.assertFalse(form_field.required)


    @test_settings
    def test_init_with_image(self):

        languages = ['de', 'fr']

        self.create_secondary_languages(languages)

        content_image = self.create_content_image()
        content_type = ContentType.objects.get_for_model(ContentImage)

        image_url = content_image.image_url()

        locale_entries = {
            '_meta' : {
            },
        }

        image_locale_key = content_image.get_image_locale_key()
        image_locale_entry = content_image.get_image_locale_entry()

        locale_entries[image_locale_key] = image_locale_entry

        if not self.meta_app.localizations:
            self.meta_app.localizations = {}
            self.meta_app.localizations[self.meta_app.primary_language] = {}

        for key, value in locale_entries.items():
            self.meta_app.localizations[self.meta_app.primary_language][key] = value

        self.meta_app.save()

        primary_locale = self.meta_app.localizations[self.meta_app.primary_language]

        language_code = 'de'
        field_name_utf8 = '{0}-{1}'.format(language_code, image_locale_key)
        field_name = base64.b64encode(field_name_utf8.encode()).decode()

        # init without existing translated image
        form = TranslateAppForm(self.meta_app)

        field = form.fields[field_name]
        
        self.assertTrue(isinstance(field, forms.ImageField))
        self.assertEqual(field.widget.instance, None)

        # init with existing translated image
        localized_content_image = LocalizedContentImage(
            image_store = content_image.image_store,
            content_image=content_image,
            language_code=language_code,
        )

        localized_content_image.save()

        form = TranslateAppForm(self.meta_app)
        field = form.fields[field_name]

        self.assertTrue(isinstance(field, forms.ImageField))

        self.assertEqual(field.widget.instance, localized_content_image)
        

    @test_settings
    def test_clean(self):

        languages = ['de', 'fr']

        self.create_secondary_languages(languages)

        locale_entries = self.create_locale_entries()

        post_data = {}

        unbound_form = TranslateAppForm(self.meta_app)
        for field in unbound_form:
            post_data[field.name] = field.name

        form = TranslateAppForm(self.meta_app, data=post_data)
        form.cleaned_data = post_data
        form._clean_fields()
        cleaned_data = form.clean()

        self.assertTrue(hasattr(form, 'translations'))

        for language in languages:
            self.assertIn(language, form.translations)

        for b64_key, value in form.cleaned_data.items():
            field_name = base64.b64decode(b64_key).decode()
            parts = field_name.split('-')
            language = parts[0]
            key = '-'.join(parts[1:])

            self.assertIn(key, form.translations[language])       

        
class TestBuildAppForm(WithFormTest, WithMetaApp, TenantTestCase):

    @test_settings
    def test_bound(self):

        form = BuildAppForm()

        post_data = {
            'platforms' : ['android'],
        }


        self.perform_form_test(BuildAppForm, post_data)


class TestZipImportForm(WithFormTest, WithMetaApp, WithZipFile, TenantTestCase):

    @test_settings
    def test_bound(self):

        form = ZipImportForm()

        post_data = {
            'zipfile' : self.get_zip_file,
        }


        self.perform_form_test(ZipImportForm, {}, file_data=post_data)


class TestTranslateVernacularNamesForm(WithFormTest, WithMetaVernacularNames, WithMetaApp, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        
        self.taxon = lacerta_agilis
        
        self.create_secondary_languages(['de',])
    
    @test_settings
    def test_init(self):
        
        form = TranslateVernacularNamesForm(self.meta_app)
        
        self.assertEqual(form.page, 1)
        
        form = TranslateVernacularNamesForm(self.meta_app, page=2)
        
        self.assertEqual(form.page, 2)
        
        self.assertEqual(form.fields, {})
        
        # form with fields
        mvn = self.create_mvn(self.taxon, 'Localized name', self.meta_app.primary_language)
        
        all_vernacular_names = MetaVernacularNames.objects.filter(language=self.meta_app.primary_language).order_by('name')
        self.assertEqual(all_vernacular_names.count(), 1)

        form = TranslateVernacularNamesForm(self.meta_app)

        key = 'mvn-{0}-de'.format(mvn.pk)
        self.assertIn(key, form.fields)
        
        form_field = form.fields[key]
        self.assertEqual(form_field.taxon, self.taxon)
        self.assertEqual(form_field.language, 'de')
        self.assertEqual(form_field.is_first, True)
        self.assertEqual(form_field.is_last, True)
        
    
    @test_settings
    def test_clean(self):
        
        post_data = {}        
        # form with fields
        mvn = self.create_mvn(self.taxon, 'Localized name', self.meta_app.primary_language)
        
        form = TranslateVernacularNamesForm(self.meta_app, data=post_data)
        
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        expected_translations = {
            'de': [
                {
                    'taxon': self.taxon,
                    'name': None
                }
            ]
        }
        
        self.assertEqual(expected_translations, form.translations)
        
        key = 'mvn-{0}-de'.format(mvn.pk)
        post_data[key] = 'Test name'
        
        form = TranslateVernacularNamesForm(self.meta_app, data=post_data)
        
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        expected_translations = {
            'de': [
                {
                    'taxon': self.taxon,
                    'name': 'Test name'
                }
            ]
        }
        
        self.assertEqual(expected_translations, form.translations)
        
    @test_settings
    def test_initial(self):
       
        # form with fields
        mvn = self.create_mvn(self.taxon, 'Localized name', self.meta_app.primary_language)

        mvn_2 = self.create_mvn(self.taxon, 'Test name', 'de')
        
        form = TranslateVernacularNamesForm(self.meta_app)
        
        key = 'mvn-{0}-de'.format(mvn.pk)
        
        self.assertEqual(form.fields[key].initial, 'Test name')
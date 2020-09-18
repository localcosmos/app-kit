from django.test import TestCase, RequestFactory
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from django.urls import reverse

from app_kit.tests.common import test_settings, TEST_BACKGROUND_IMAGE_PATH

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithImageStore, WithFormTest, ViewTestMixin,
                                  WithMedia)

from app_kit.views import (TenantPasswordResetView, CreateGenericContent, CreateApp, GetAppCard,
            AppLimitReached, DeleteApp, CreateGenericAppContent, GetGenericContentCard, ManageGenericContent,
            EditGenericContentName, ManageApp, TranslateApp, BuildApp, StartNewAppVersion,
            AddExistingGenericContent, ListManageApps, RemoveAppGenericContent, ManageAppLanguages,
            DeleteAppLanguage, AddTaxonomicRestriction, RemoveTaxonomicRestriction, ManageContentImageMixin,
            ManageContentImage, ManageContentImageWithText, DeleteContentImage, ManageAppThemeImage,
            DeleteAppThemeImage, GetAppThemeImageFormField, StoreObjectOrder, MockButton, ManageAppDesign,
            ImportFromZip, IdentityMixin, LegalNotice, PrivacyStatement)

from app_kit.forms import (CreateGenericContentForm, CreateAppForm, EditGenericContentNameForm,
                           TranslateAppForm, AddExistingGenericContentForm, AddLanguageForm, AppDesignForm,
                           ManageContentImageForm, ManageContentImageWithTextForm, AppThemeImageForm)

from app_kit.models import MetaApp, MetaAppGenericContent, ContentImage
from app_kit.features.nature_guides.models import NatureGuide
from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy
from app_kit.features.generic_forms.models import GenericForm, GenericField, GenericFieldToGenericForm

from app_kit.AppThemeImage import AppThemeImage
from app_kit.AppThemeText import AppThemeText

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from content_licencing.licences import ContentLicence


import hashlib, base64, os, json
        

class TestTenantPasswordResetView(WithLoggedInUser, WithUser, WithTenantClient, TenantTestCase):

    @test_settings
    def test_dispatch(self):

        response = self.tenant_client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 200)
        

# Use CreateApp url for testing
class TestCreateGenericContent(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                               TenantTestCase):

    url_name = 'create_app'
    view_class = CreateGenericContent

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(MetaApp)


    def get_view(self):
        view = super().get_view()
        view.generic_content_type_id = self.content_type.id

        return view


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()

        context = view.get_context_data()
            
        self.assertEqual(context['content_type_id'], self.content_type.id)
        self.assertEqual(context['content_type'], self.content_type)
        

    @test_settings
    def test_get_initial(self):

        view = self.get_view()

        initial = view.get_initial()

        self.assertEqual(initial['content_type_id'], self.content_type.id)


    @test_settings
    def test_get_create_kwargs(self):

        view = self.get_view()
        kwargs = view.get_create_kwargs(view.request)
        self.assertEqual(kwargs, {})
        

    @test_settings
    def test_save(self):

        content_type = ContentType.objects.get_for_model(NatureGuide)

        post_data = {
            'name' : 'Test Generic Content',
            'content_type_id' : content_type.id,
            'input_language' : 'en',
        }

        form = CreateGenericContentForm(post_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()
        
        view.primary_language = 'en'
        view.kwargs = {}
        view.generic_content_type_id = content_type.id

        context = view.save(form)
        nature_guide = NatureGuide.objects.all().last()

        self.assertEqual(context['created_content'], nature_guide)
        

    @test_settings
    def test_form_valid(self):

        content_type = ContentType.objects.get_for_model(NatureGuide)

        post_data = {
            'name' : 'Test Generic Content',
            'content_type_id' : content_type.id,
            'input_language' : 'en',
        }

        form = CreateGenericContentForm(post_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()
        view.primary_language = 'en'
        view.kwargs = {}
        view.generic_content_type_id = content_type.id

        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)



class TestCreateApp(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                    TenantTestCase):


    url_name = 'create_app'
    view_class = CreateApp

    def get_request(self, ajax=True):
        request = super().get_request(ajax=ajax)
        request.LANGUAGE_CODE = 'en'
        return request


    def get_view(self):

        view = super().get_view()

        self.content_type = ContentType.objects.get_for_model(MetaApp)
        view.generic_content_type_id = self.content_type.id

        return view
        

    @test_settings
    def test_get_form_kwargs(self):

        view = self.get_view()

        form_kwargs = view.get_form_kwargs()
        self.assertFalse('allow_uuid' in form_kwargs)

        view.request.user = self.superuser
            
        form_kwargs = view.get_form_kwargs()
        self.assertTrue(form_kwargs['allow_uuid'])
        

    @test_settings
    def test_get_initial(self):

        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial['primary_language'], 'en')


    @test_settings
    def test_set_primary_language(self):

        view = self.get_view()

        post_data = {
            'name' : 'Test Generic Content',
            'content_type_id' : self.content_type.id,
            'input_language' : 'en',
            'primary_language' : 'en',
            'subdomain' : 'testapp',
        }

        form = CreateAppForm(post_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})
        
        view.form = form
        view.set_primary_language(view.request)
        
        self.assertEqual(view.primary_language, 'en')


    @test_settings
    def test_set_content_type_id(self):

        view = self.get_view()
        view.generic_content_type_id = None
        view.set_content_type_id()

        self.assertEqual(view.generic_content_type_id, self.content_type.id)
        

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()

        context_data = view.get_context_data()
        self.assertEqual(context_data['is_app_creation'], True)


    @test_settings
    def test_save(self):

        self.create_public_domain()

        view = self.get_view()
        view.kwargs = {}

        post_data = {
            'name' : 'Test Generic Content',
            'content_type_id' : self.content_type.id,
            'input_language' : 'en',
            'primary_language' : 'en',
            'subdomain' : 'testapp',
        }

        form = CreateAppForm(post_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        context = view.save(form)

        meta_app = MetaApp.objects.all().last()
        self.assertEqual(context['meta_app'], meta_app)
        self.assertEqual(context['created_content'], meta_app)

        self.assertEqual(meta_app.primary_language, post_data['primary_language'])
        self.assertEqual(meta_app.name, post_data['name'])



class TestGetAppCard(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                     WithMetaApp, TenantTestCase):

    url_name = 'get_app_card'
    view_class = GetAppCard

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }

        return url_kwargs
        

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.meta_app = self.meta_app
        context = view.get_context_data()
        content_type = ContentType.objects.get_for_model(MetaApp)
        self.assertEqual(context['content_type'], content_type)


class TestAppLimitReached(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                          TenantTestCase):

    url_name = 'app_limit_reached'


class TestDeleteApp(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient, WithMetaApp,
                    TenantTestCase):

    url_name = 'delete_app'
    view_class = DeleteApp

    def get_url_kwargs(self):

        url_kwargs = {
            'pk' : self.meta_app.pk,
        }
        return url_kwargs
        

    @test_settings
    def test_delete(self):

        meta_app_id = self.meta_app.pk

        view = self.get_view()

        response = view.delete(view.request)
        self.assertEqual(response.status_code, 200)

        exists = MetaApp.objects.filter(pk=meta_app_id).exists()
        self.assertFalse(exists)
        

class TestCreateGenericAppContent(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                  WithTenantClient, WithMetaApp, TenantTestCase):

    url_name = 'create_generic_appcontent'
    view_class = CreateGenericAppContent

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
        
    @test_settings
    def test_set_content_type(self):

        view = self.get_view()
        view.set_content_type_id(**view.kwargs)
        self.assertEqual(view.generic_content_type_id, self.content_type.id)
        self.assertEqual(view.generic_content_type, self.content_type)
        

    @test_settings
    def test_set_primary_language(self):
        view = self.get_view()
        view.set_primary_language(view.request, **view.kwargs)
        self.assertEqual(view.primary_language, self.meta_app.primary_language)
        

    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.primary_language = 'en'
        view.generic_content_type_id = self.content_type.id
        initial = view.get_initial()
        self.assertEqual(initial['input_language'], 'en')

    @test_settings
    def test_get_form_kwargs(self):

        view = self.get_view()
        view.primary_language = 'en'
        view.set_content_type_id(**view.kwargs)
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['language'], 'en')

    @test_settings
    def test_get_context_data(self):

        # allowed
        view = self.get_view()
        view.primary_language = 'en'
        view.set_content_type_id(**view.kwargs)

        context = view.get_context_data()
        self.assertEqual(context['meta_app'], self.meta_app)
        self.assertEqual(context['disallow_single_content'], False)

        # unaddable
        self.content_type = ContentType.objects.get_for_model(BackboneTaxonomy)

        bbt_link = MetaAppGenericContent.objects.get(
            meta_app=self.meta_app,
            content_type=self.content_type,
        )

        view_2 = self.get_view()
        view_2.primary_language = 'en'
        view_2.set_content_type_id(**view_2.kwargs)
        
        context_2 = view_2.get_context_data()
        self.assertEqual(context_2['meta_app'], self.meta_app)
        self.assertEqual(context_2['disallow_single_content'], True)
        

    @test_settings
    def test_save(self):

        content_type = ContentType.objects.get_for_model(NatureGuide)

        post_data = {
            'name' : 'Test Generic Content',
            'content_type_id' : content_type.id,
            'input_language' : 'en',
        }

        form = CreateGenericContentForm(post_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()
        view.primary_language = 'en'
        view.set_content_type_id(**view.kwargs)

        context = view.save(form)
        nature_guide = NatureGuide.objects.all().last()

        self.assertEqual(context['created_content'], nature_guide)
        self.assertEqual(context['meta_app'], self.meta_app)

        applink = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=content_type)
        self.assertEqual(context['link'], applink)


class TestGetGenericContentCard(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                                WithMetaApp, TenantTestCase):

    url_name = 'generic_content_card'
    view_class = GetGenericContentCard

    def setUp(self):
        super().setUp()
        self.create_all_generic_contents(self.meta_app)
        self.content_type = ContentType.objects.get_for_model(NatureGuide)


    def get_url_kwargs(self):
        link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=self.content_type)
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_content_link_id' :link.id,
        }
        return url_kwargs
        

    @test_settings
    def test_get_context_data(self):

        link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=self.content_type)

        view = super().get_view()
        view.meta_app = self.meta_app
        view.link = link

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['link'], link)


class TestManageGenericContent(ViewTestMixin, WithLoggedInUser, WithUser, WithTenantClient, WithMetaApp,
                               TenantTestCase):

    url_name = 'manage_metaapp'
    view_class = ManageGenericContent

    def setUp(self):
        super().setUp()
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(NatureGuide)
        self.generic_content = self.link.generic_content
        self.content_type = ContentType.objects.get_for_model(NatureGuide)

    def get_url_kwargs(self):
        
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }

        return url_kwargs

    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
        

    @test_settings
    def test_set_content(self):
        view = self.get_view()
        view.set_content()
        self.assertEqual(view.generic_content_type, self.content_type)
        self.assertEqual(view.generic_content, self.generic_content)

    @test_settings
    def test_set_languages(self):

        view = self.get_view()
        view.set_languages()
        self.assertEqual(view.primary_language, self.meta_app.primary_language)
        self.assertEqual(view.languages, self.meta_app.languages())


    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.set_content()
        view.set_languages()

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['generic_content'], self.generic_content)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['languages'], self.meta_app.languages())
        self.assertEqual(context['primary_language'], self.meta_app.primary_language)
        self.assertEqual(context['meta_app'], self.meta_app)
        

    @test_settings
    def test_get_options_form_kwargs(self):

        view = self.get_view()
        view.set_content()
        view.set_languages()

        form_kwargs = view.get_options_form_kwargs()
        self.assertEqual(form_kwargs['meta_app'], self.meta_app)
        self.assertEqual(form_kwargs['generic_content'], self.generic_content)
        self.assertEqual(form_kwargs['initial'], {})


    @test_settings
    def test_get_initial(self):

        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial, {})
        

    @test_settings
    def test_verbose_view_name(self):
        view = self.get_view()
        verbose_name = view.verbose_view_name(**view.kwargs)

        self.assertEqual(verbose_name, str(view.generic_content))


class TestManageApp(ViewTestMixin, WithAdminOnly, WithLoggedInUser, WithUser, WithTenantClient, WithMetaApp,
                    TenantTestCase):


    url_name = 'manage_metaapp'
    view_class = ManageApp

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(MetaApp)


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.meta_app.id,
        }
        return url_kwargs

    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
        

    '''
    this tests test ManageGenericContent.post for a view without options_form_class
    '''
    @test_settings
    def test_post_no_options_form(self):

        view = self.get_view()
        view.set_content()
        view.set_languages()

        # no options form
        view.request.POST = {}
        view.options_form_class = None
        
        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['posted'], True)
        self.assertEqual(response.context_data['options_form'], None)
        self.assertEqual(response.context_data['saved_options'], False)


    @test_settings
    def test_post_with_options_form(self):
        # set a view.options_form_class
        # all fields are global options
        post_data = {
            'allow_anonymous_observations' : True,
        }

        view = self.get_view()
        view.set_content()
        view.set_languages()

        view.request.POST = post_data

        self.assertEqual(self.meta_app.global_options, {})
        
        response = view.post(view.request, **view.kwargs)
        self.meta_app.refresh_from_db()

        self.assertEqual(self.meta_app.global_options, post_data)
        self.assertEqual(response.status_code, 200)

        # remove an element
        view_2 = self.get_view()
        view_2.set_content()
        view_2.set_languages()
        post_data_2 = {
            'allow_anonymous_observations' : False,
        }
        view_2.request.post_data = post_data_2
        response_2 = view_2.post(view_2.request, **view_2.kwargs)
        self.meta_app.refresh_from_db()
        self.assertEqual(self.meta_app.global_options, {})
        self.assertEqual(response_2.status_code, 200)



class TestEditGenericContentName(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                                 WithMetaApp, TenantTestCase):

    url_name = 'edit_generic_content_name'
    view_class = EditGenericContentName
    
    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(NatureGuide)
        self.generic_content = self.link.generic_content


    def get_url_kwargs(self):
        url_kwargs = {
            'content_type_id' : self.content_type.id,
            'generic_content_id' : self.generic_content.id,
        }
        return url_kwargs
    

    def get_view(self):

        view = super().get_view()
        view.meta_app = self.meta_app
        view.generic_content_type = self.content_type
        view.generic_content = self.generic_content
        view.primary_language = self.generic_content.primary_language

        return view

    @test_settings
    def test_set_content(self):
        view = self.get_view()
        view.set_content()
        self.assertEqual(view.generic_content_type, self.content_type)
        self.assertEqual(view.generic_content, self.generic_content)
        self.assertEqual(view.primary_language, 'en')
        
    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_content()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['generic_content'], self.generic_content)


    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.set_content()

        initial = view.get_initial()

        self.assertEqual(initial['content_type_id'], self.content_type.id)
        self.assertEqual(initial['generic_content_id'], self.generic_content.id)
        self.assertEqual(initial['name'], self.generic_content.name)
        

    @test_settings
    def test_get_form_kwargs(self):
        view = self.get_view()
        view.set_content()

        form_kwargs = view.get_form_kwargs()

        self.assertEqual(form_kwargs['language'], 'en')


    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.set_content()

        new_name = 'new name'

        post_data = {
            'content_type_id' : self.content_type.id,
            'generic_content_id' : self.generic_content.id,
            'name' : new_name,
            'input_language' : 'en',
        }

        form = EditGenericContentNameForm(post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.generic_content.refresh_from_db()
        self.assertEqual(self.generic_content.name, new_name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['generic_content'], self.generic_content)


    @test_settings
    def test_form_valid_metaapp(self):

        view = self.get_view()
        view.set_content()

        new_name = 'new name'

        app_type = ContentType.objects.get_for_model(MetaApp)

        post_data = {
            'content_type_id' : app_type.id,
            'generic_content_id' : self.meta_app.id,
            'name' : new_name,
            'input_language' : 'en',
        }

        form = EditGenericContentNameForm(post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.meta_app.refresh_from_db()
        self.assertEqual(self.meta_app.name, new_name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['generic_content'], self.meta_app)

    

class TestTranslateApp(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                                 WithMetaApp, TenantTestCase):

    url_name = 'translate_app'
    view_class = TranslateApp

    def setUp(self):
        super().setUp()
        languages = ['de', 'fr']
        self.create_secondary_languages(languages)

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view

    @test_settings
    def test_update_translation_files(self):
        view = self.get_view()
        view.update_translation_files(**view.kwargs)

        # check if the primary locale exists
        appbuilder = self.meta_app.get_preview_builder()
        primary_locale = appbuilder.get_primary_locale(self.meta_app)
        self.assertIn(self.meta_app.name, primary_locale)
        

    @test_settings
    def test_get_form_kwargs(self):

        view = self.get_view()
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['page'], 1)

        view.request.GET = {
            'page' : '2'
        }

        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['page'], 2)
        
    @test_settings
    def test_get_form(self):

        view = self.get_view()
        form = view.get_form()
        self.assertEqual(form.__class__, TranslateAppForm)

    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.update_translation_files(**view.kwargs)

        # c&p from TranslateAppForm
        field_name_utf8 = '{0}-{1}'.format('de', self.meta_app.name)
        field_name = base64.b64encode(field_name_utf8.encode()).decode()
        

        post_data = {}
        app_name_de = 'new app name de'
        post_data[field_name] = app_name_de

        form = TranslateAppForm(self.meta_app, data=post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['saved'], True)
        self.assertEqual(response.context_data['form'].__class__, TranslateAppForm)

        appbuilder = self.meta_app.get_preview_builder()
        de_locale = appbuilder.get_locale(self.meta_app, 'de')
        self.assertEqual(de_locale[self.meta_app.name], app_name_de)


class TestBuildApp(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                                 WithMetaApp, TenantTestCase):

    url_name = 'build_app'
    view_class = BuildApp

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }

        return url_kwargs

    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view

    @test_settings
    def test_get_initial(self):

        # no build settings, no initial
        view = self.get_view()
        initial = view.get_initial()

        self.assertEqual(initial, {})

        platforms = ['Android', 'iOS']
        self.meta_app.build_settings = {
            'platforms' : platforms,
        }

        self.meta_app.save()
        view_2 = self.get_view()
        initial_2 = view_2.get_initial()
        self.assertEqual(initial_2['platforms'], platforms)
        self.assertEqual(initial_2['distribution'], 'appstores')


    @test_settings
    def test_get_context_data(self):
        pass


    @test_settings
    def test_form_valid(self):
        pass


class TestStartNewAppVersion(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                                 WithMetaApp, TenantTestCase):

    url_name = 'start_new_app_version'
    view_class = StartNewAppVersion

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view


    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['meta_app'], self.meta_app)


    @test_settings
    def test_post_donothing(self):
        view = self.get_view()

        response = view.post(view.request)
        self.assertEqual(response.status_code, 302) 
        self.assertIn('manage-app', response.url)

        self.meta_app.refresh_from_db()
        self.assertEqual(self.meta_app.current_version, 1)
        

    @test_settings
    def test_post_new_version(self):

        view = self.get_view()
        # equal versions trigger starting a new one
        self.meta_app.published_version = self.meta_app.current_version
        self.meta_app.save()

        # no form or post_data is required
        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 302) 
        self.assertIn('manage-app', response.url)

        self.meta_app.refresh_from_db()
        self.assertEqual(self.meta_app.current_version, 2)

        appbuilder = self.meta_app.get_preview_builder()
        version_1_folder = appbuilder._app_version_root_folder(self.meta_app, app_version=1)
        version_2_folder = appbuilder._app_version_root_folder(self.meta_app, app_version=2)

        self.assertTrue(os.path.isdir(version_2_folder))
        self.assertTrue(os.path.isdir(version_1_folder))
        

    @test_settings
    def test_post_delete_one_version(self):

        view = self.get_view()
        # equal versions trigger starting a new one
        self.meta_app.published_version = self.meta_app.current_version
        self.meta_app.save()

        # no form or post_data is required
        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 302) 
        self.assertIn('manage-app', response.url)

        self.meta_app.refresh_from_db()
        self.assertEqual(self.meta_app.current_version, 2)

        self.meta_app.published_version = self.meta_app.current_version
        response = view.post(view.request, **view.kwargs)

        appbuilder = self.meta_app.get_preview_builder()
        version_1_folder = appbuilder._app_version_root_folder(self.meta_app, app_version=1)
        version_2_folder = appbuilder._app_version_root_folder(self.meta_app, app_version=2)
        version_3_folder = appbuilder._app_version_root_folder(self.meta_app, app_version=3)

        self.assertTrue(os.path.isdir(version_3_folder))
        self.assertTrue(os.path.isdir(version_2_folder))
        self.assertFalse(os.path.isdir(version_1_folder))
        
        
        
class TestAddExistingGenericContent(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                    WithTenantClient, WithMetaApp, TenantTestCase):

    url_name = 'add_existing_generic_content'
    view_class = AddExistingGenericContent

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(NatureGuide)
        self.generic_content = self.link.generic_content
        self.link.delete()

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
        }

        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.generic_content_type = self.content_type

        return view


    @test_settings
    def test_get_form(self):

        view = self.get_view()
        form = view.get_form()
        self.assertEqual(form.__class__, AddExistingGenericContentForm)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['meta_app'], self.meta_app)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['disallow_single_content'], False)
        self.assertEqual(context['content_model'], self.content_type.model_class())


    @test_settings
    def form_valid(self):

        post_data = {
            'generic_content' : self.generic_content.id,
        }

        form = AddExistingGenericContentForm(self.meta_app, self.content_type, data=post_data)

        is_valid = form.is_valid()
        self.assertTrue(is_valid)

        exists = MetaAppGenericContent.objects.filter(meta_app=self.meta_app,
                                                      content_type=self.content_type).exists()
        self.assertFalse(exists)

        view = self.get_view()
        response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['added_contents'], [self.generic_content])
        link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=self.content_type)
        self.assertEqual(response.context_data['added_links'], [link])


class TestListManageApps(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                    WithTenantClient, WithMetaApp, TenantTestCase):

    url_name = 'appkit_home'
    view_class = ListManageApps

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)

        app_content_type = ContentType.objects.get_for_model(MetaApp)
        self.assertEqual(context['content_type'], app_content_type)
        self.assertEqual(len(context['meta_apps']), 1)
        self.assertEqual(context['meta_apps'][0], self.meta_app)
        

class TestRemoveAppGenericContent(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                    WithTenantClient, WithMetaApp, TenantTestCase):

    url_name = 'remove_app_generic_content'
    view_class = RemoveAppGenericContent

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(NatureGuide)
        self.generic_content = self.link.generic_content
        
    def get_url_kwargs(self):
        url_kwargs = {
            'pk' : self.link.id,
        }
        return url_kwargs

    @test_settings
    def get_context_data(self):

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['meta_app'], self.meta_app)


class TestManageAppLanguages(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                             WithMetaApp, TenantTestCase):

    url_name = 'manage_app_languages'
    view_class = ManageAppLanguages

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['meta_app'], self.meta_app)
        self.assertEqual(context['generic_content'], self.meta_app)
        app_type = ContentType.objects.get_for_model(MetaApp)
        self.assertEqual(context['content_type'], app_type)
        self.assertEqual(context['languages'], ['en'])
        self.assertEqual(context['primary_language'], 'en')
        self.assertEqual(context['form'].__class__, AddLanguageForm)


class TestAddAppLanguages(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                          WithMetaApp, TenantTestCase):

    url_name = 'add_app_languages'
    view_class = ManageAppLanguages

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'action' : 'add',
        }
        return url_kwargs

    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view

    @test_settings
    def test_post(self):

        view = self.get_view()
        view.request.POST = {
            'language' : 'de'
        }

        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.context_data['languages'], ['en', 'de'])
        self.assertEqual(response.context_data['primary_language'], 'en')
        self.assertEqual(response.context_data['form'].__class__, AddLanguageForm)
        


class TestDeleteAppLanguage(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                            WithMetaApp, TenantTestCase):

    url_name = 'delete_app_language'
    view_class = DeleteAppLanguage

    def setUp(self):
        super().setUp()
        languages = ['de', 'fr']
        self.create_secondary_languages(languages)

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'language' : 'de',
        }
        return url_kwargs

    @test_settings
    def test_get_object(self):
        view = self.get_view()
        view.object = view.get_object()
        language = view.get_object()
        self.assertEqual(language.app, self.meta_app.app)
        self.assertEqual(language.language_code, 'de')

    @test_settings
    def test_get_verbose_name(self):
        view = self.get_view()
        view.object = view.get_object()
        name = view.get_verbose_name()
        self.assertEqual(name, 'de')

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.object = view.get_object()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['language'], 'de')


    
class TestAddTaxonomicRestriction(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                            WithMetaApp, TenantTestCase):

    url_name = 'add_taxonomic_restriction'
    view_class = AddTaxonomicRestriction

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(GenericForm)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(GenericForm)
        self.generic_content = self.link.generic_content

    def get_url_kwargs(self):
        url_kwargs = {
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return url_kwargs

    @test_settings
    def test_get_taxon_search_url(self):

        view = self.get_view()
        url = view.get_taxon_search_url()

    @test_settings
    def test_get_availability(self):
        view = self.get_view()
        availability = view.get_availability()
        self.assertTrue(availability)


'''
    This test uses a generic content instance as the Content the image is assigned to
'''
class ContentImagePostData:

    def get_post_form_data(self, image_type='image'):
        crop_parameters = {
            'width' : 12,
            'height' : 20,
        }

        md5_image = self.get_image()
        correct_md5 = hashlib.md5(md5_image.read()).hexdigest()
        
        post_data = {
            'md5' : correct_md5,
            'crop_parameters' : json.dumps(crop_parameters),
        }

        file_data = {
            'source_image' : self.get_image(),
        }

        licencing_data = self.get_licencing_post_data()
        post_data.update(licencing_data)

        return post_data, file_data


    def create_content_image(self):
        image_store = self.create_image_store()

        content_image = ContentImage(
            image_store = image_store,
            content_type = self.content_type,
            object_id = self.generic_content.id,
        )

        content_image.save()

        return content_image

    
class TestManageContentImageMixin(ContentImagePostData, WithLoggedInUser, WithUser, WithTenantClient,
                                  WithMetaApp, WithImageStore, WithMedia, WithFormTest, TenantTestCase):

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(NatureGuide)
        self.generic_content = self.link.generic_content


    def get_url(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return reverse('manage_content_image', kwargs=url_kwargs)


    def get_request(self):
        factory = RequestFactory()
        url = self.get_url()
        
        request = factory.get(url)
        request.user = self.user
        request.session = self.client.session
        request.tenant = self.tenant

        return request
        

    @test_settings
    def test_set_content_image(self):        

        # content_type_id and object_id in kwargs
        # case 1: content_image_id not in kwargs, new image, cutom iamge type
        image_type_kwargs = {
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
            'image_type' : 'custom',
        }

        request = self.get_request()
        request.GET = {}
        mixin = ManageContentImageMixin()
        mixin.request = request
        mixin.set_content_image(**image_type_kwargs)
        self.assertEqual(mixin.image_type, 'custom')
        self.assertEqual(mixin.content_image, None)
        self.assertEqual(mixin.object_content_type, self.content_type)
        self.assertEqual(mixin.content_instance, self.generic_content)
        self.assertTrue(mixin.new)

        # case 2: content_image_id not in kwargs, not a new image
        content_type_kwargs = {
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        
        request_2 = self.get_request()
        request_2.GET = {}
        mixin_2 = ManageContentImageMixin()
        mixin_2.request = request_2
        mixin_2.set_content_image(**content_type_kwargs)
        self.assertEqual(mixin_2.image_type, 'image')
        self.assertEqual(mixin_2.content_image, None)
        self.assertEqual(mixin_2.object_content_type, self.content_type)
        self.assertEqual(mixin_2.content_instance, self.generic_content)
        self.assertTrue(mixin_2.new)

        ### IMAGE EXISTS
        # test with existing content image
        content_image = self.create_content_image()

        # case 3: image exists, content_type_kwargs, not new
        request_3 = self.get_request()
        request_3.GET = {}
        mixin_3 = ManageContentImageMixin()
        mixin_3.request = request_3
        mixin_3.set_content_image(**content_type_kwargs)
        self.assertEqual(mixin_3.image_type, 'image')
        self.assertEqual(mixin_3.content_image, content_image)
        self.assertEqual(mixin_3.object_content_type, self.content_type)
        self.assertEqual(mixin_3.content_instance, self.generic_content)
        self.assertFalse(mixin_3.new)
        

        # case 4: content_image_id in kwargs, not new
        image_kwargs = {
            'content_image_id' : content_image.id,
        }

        mixin_4 = ManageContentImageMixin()
        mixin_4.set_content_image(**image_kwargs)
        self.assertEqual(mixin_4.image_type, 'image')
        self.assertEqual(mixin_4.content_image, content_image)
        self.assertEqual(mixin_4.object_content_type, self.content_type)
        self.assertEqual(mixin_4.content_instance, self.generic_content)
        self.assertFalse(mixin_4.new)

        # content_type_id and object_id in kwargs
        # case 5: image exists, content_image_id not in kwargs, new image
        exists_kwargs = {
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }

        request_5 = self.get_request()
        request_5.GET = {
            'new' : '1'
        }
        mixin_5 = ManageContentImageMixin()
        mixin_5.request = request_5
        mixin_5.set_content_image(**image_type_kwargs)
        self.assertEqual(mixin_5.image_type, 'custom')
        self.assertEqual(mixin_5.content_image, None)
        self.assertEqual(mixin_5.object_content_type, self.content_type)
        self.assertEqual(mixin_5.content_instance, self.generic_content)
        self.assertTrue(mixin_5.new)
        

    @test_settings
    def test_set_taxon(self):

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')

        request = self.get_request()
        request.GET = {
            'taxon_source' : taxon_source,
            'taxon_latname' : lacerta_agilis.taxon_latname,
            'taxon_author' : lacerta_agilis.taxon_author,
        }
        
        mixin = ManageContentImageMixin()
        mixin.set_taxon(request)
        self.assertEqual(str(mixin.taxon.name_uuid), str(lacerta_agilis.name_uuid))
        

    @test_settings
    def test_tree_instance(self):

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)
        
        mixin = ManageContentImageMixin()
        mixin.models = models
        mixin.taxon = lazy_taxon
        taxon = mixin.tree_instance()
        self.assertEqual(taxon, lacerta_agilis)


    @test_settings
    def test_get_new_image_store(self):
        request = self.get_request()
        request.GET = {}
        mixin = ManageContentImageMixin()
        mixin.request = request

        image_store = mixin.get_new_image_store()
        self.assertEqual(image_store.uploaded_by, request.user)


    '''
    test with form data
    '''
    def get_post_form_data(self, image_type='image'):
        crop_parameters = {
            'width' : 12,
            'height' : 20,
        }

        md5_image = self.get_image()
        correct_md5 = hashlib.md5(md5_image.read()).hexdigest()
        
        post_data = {
            'md5' : correct_md5,
            'crop_parameters' : json.dumps(crop_parameters),
        }

        file_data = {
            'source_image' : self.get_image(),
        }

        licencing_data = self.get_licencing_post_data()
        post_data.update(licencing_data)

        return post_data, file_data


    def get_mixin_for_save(self):
        content_type_kwargs = {
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        
        request = self.get_request()
        request.GET = {}
        mixin = ManageContentImageMixin()
        mixin.request = request
        mixin.set_content_image(**content_type_kwargs)
        mixin.set_taxon(request)

        return mixin
        

    @test_settings
    def test_save_image(self):

        post_data, file_data = self.get_post_form_data()
        
        form = ManageContentImageForm(data=post_data, files=file_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        # new image
        mixin = self.get_mixin_for_save()

        content_image_qry = ContentImage.objects.filter(content_type=self.content_type,
                                                        object_id=self.generic_content.id)

        self.assertFalse(content_image_qry.exists())

        mixin.save_image(form)

        # check if the content image has been created
        self.assertTrue(content_image_qry.exists())
        
        # check if the licence has been stored
        content_image = content_image_qry.first()

        licence = content_image.image_store.licences.first()
        licencing_data = self.get_licencing_post_data()
        
        self.assertEqual(licence.creator_name, licencing_data['creator_name'])
        self.assertEqual(licence.licence, 'CC0')


    @test_settings
    def test_save_image_update(self):

        content_image = self.create_content_image()

        post_data, file_data = self.get_post_form_data()
        
        form = ManageContentImageForm(data=post_data, files=file_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        # image does exist
        mixin = self.get_mixin_for_save()

        self.assertEqual(mixin.content_image, content_image)

        content_image_qry = ContentImage.objects.filter(content_type=self.content_type,
                                                        object_id=self.generic_content.id)

        self.assertTrue(content_image_qry.exists())

        mixin.save_image(form)

        # check if the content image has been created
        self.assertTrue(content_image_qry.exists())
        
        # check if the licence has been stored
        content_image = content_image_qry.first()

        licence = content_image.image_store.licences.first()
        licencing_data = self.get_licencing_post_data()
        
        self.assertEqual(licence.creator_name, licencing_data['creator_name'])
        self.assertEqual(licence.licence, 'CC0')
        

    @test_settings
    def test_save_image_with_text(self):

        post_data, file_data = self.get_post_form_data()
        text = 'Test text'
        post_data['text'] = text
        
        form = ManageContentImageWithTextForm(data=post_data, files=file_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        # new image
        mixin = self.get_mixin_for_save()

        content_image_qry = ContentImage.objects.filter(content_type=self.content_type,
                                                        object_id=self.generic_content.id)

        self.assertFalse(content_image_qry.exists())

        mixin.save_image(form)

        # check if the content image has been created
        self.assertTrue(content_image_qry.exists())
        
        # check if the licence has been stored
        content_image = content_image_qry.first()
        self.assertEqual(content_image.text, text)


    @test_settings
    def test_save_image_custom_type(self):

        post_data, file_data = self.get_post_form_data()
        image_type = 'custom'
        post_data['image_type'] = image_type
        
        form = ManageContentImageForm(data=post_data, files=file_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        # new image
        mixin = self.get_mixin_for_save()

        content_image_qry = ContentImage.objects.filter(content_type=self.content_type,
                                                        object_id=self.generic_content.id)

        self.assertFalse(content_image_qry.exists())

        mixin.save_image(form)

        # check if the content image has been created
        self.assertTrue(content_image_qry.exists())
        
        # check if the licence has been stored
        content_image = content_image_qry.first()
        self.assertEqual(content_image.image_type, image_type)

        

    @test_settings
    def test_get_context_data(self):

        content_type_kwargs = {
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        
        request = self.get_request()
        request.GET = {}
        # mixin has no super, use the view instead
        mixin = ManageContentImage()
        mixin.request = request
        mixin.meta_app = self.meta_app
        mixin.set_content_image(**content_type_kwargs)
        mixin.set_taxon(request)

        context = mixin.get_context_data()
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['content_instance'], self.generic_content)
        self.assertEqual(context['content_image'], None)
        self.assertEqual(context['content_image_taxon'], None)
        self.assertEqual(context['new'], True)


    @test_settings
    def test_get_initial(self):

        content_type_kwargs = {
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        
        request = self.get_request()
        request.GET = {}
        # mixin has no super, use the view instead
        mixin = ManageContentImage()
        mixin.meta_app = self.meta_app
        mixin.request = request
        mixin.licence_registry_entry = None
        mixin.set_content_image(**content_type_kwargs)
        

        initial = mixin.get_initial()
        self.assertEqual(initial['image_type'], 'image')
        self.assertEqual(initial['uploader'], self.user)

        content_image = self.create_content_image()
        mixin_2 = ManageContentImage()
        mixin_2.request = request
        mixin_2.meta_app = self.meta_app
        mixin_2.licence_registry_entry = None
        mixin_2.set_content_image(**content_type_kwargs)

        initial_2 = mixin_2.get_initial()
        self.assertEqual(initial_2['crop_parameters'], content_image.crop_parameters)
        self.assertEqual(initial_2['image_type'], content_image.image_type)
        self.assertEqual(initial_2['text'], content_image.text)

        licencing_initial = mixin_2.get_licencing_initial()
        for key, value in licencing_initial.items():
            self.assertEqual(initial_2[key], value)


        
    @test_settings
    def test_get_form_kwargs(self):

        self.create_content_image()

        content_type_kwargs = {
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        
        request = self.get_request()
        request.GET = {}
        # mixin has no super, use the view instead
        mixin = ManageContentImage()
        mixin.meta_app = self.meta_app
        mixin.request = request
        mixin.licence_registry_entry = None
        mixin.set_content_image(**content_type_kwargs)

        form_kwargs = mixin.get_form_kwargs()
        self.assertIn('current_image', form_kwargs)


class TestManageContentImage(ViewTestMixin, WithAjaxAdminOnly, ContentImagePostData,  WithLoggedInUser,
            WithUser, WithTenantClient, WithMetaApp, WithImageStore, WithMedia, WithFormTest, TenantTestCase):

    url_name = 'manage_content_image'
    view_class = ManageContentImage

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(NatureGuide)
        self.generic_content = self.link.generic_content
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return url_kwargs


    @test_settings
    def test_form_valid(self):

        post_data, file_data = self.get_post_form_data()

        form = ManageContentImageForm(data=post_data, files=file_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()
        view.set_content_image(**view.kwargs)
        view.set_taxon(view.request)
        view.licence_registry_entry = None
        view.meta_app = self.meta_app

        content_image_qry = ContentImage.objects.filter(content_type=self.content_type,
                                                        object_id=self.generic_content.id)
        self.assertFalse(content_image_qry.exists())

        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)

        # check image existance
        # check if the content image has been created
        self.assertTrue(content_image_qry.exists())
        
        # check if the licence has been stored
        content_image = content_image_qry.first()

        licence = content_image.image_store.licences.first()
        licencing_data = self.get_licencing_post_data()
        
        self.assertEqual(licence.creator_name, licencing_data['creator_name'])
        self.assertEqual(licence.licence, 'CC0')


class TestManageContentImageWithText(ViewTestMixin, WithAjaxAdminOnly, ContentImagePostData,  WithLoggedInUser,
            WithUser, WithTenantClient, WithMetaApp, WithImageStore, WithMedia, WithFormTest, TenantTestCase):

    url_name = 'manage_content_image_with_text'
    view_class = ManageContentImageWithText


    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(NatureGuide)
        self.generic_content = self.link.generic_content
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return url_kwargs


class TestDeleteContentImage(ViewTestMixin, WithAjaxAdminOnly, ContentImagePostData, WithLoggedInUser, WithUser,
                             WithTenantClient, WithMetaApp, WithImageStore, WithMedia, TenantTestCase):

    url_name = 'delete_content_image'
    view_class = DeleteContentImage

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(NatureGuide)
        self.generic_content = self.link.generic_content

    def get_url_kwargs(self):
        content_image = self.create_content_image()
        url_kwargs = {
            'pk' : content_image.pk,
        }
        return url_kwargs

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.object = view.get_object()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['image_type'], 'image')
        self.assertEqual(context['content_instance'], self.generic_content)



class WithAppThemeImage:
    
    def get_licence_as_dict(self):

        content_licence = ContentLicence('CC0')
        licence = {
            'creator_name' : 'James Bond',
            'licence' : content_licence.as_dict(),
            'creator_link' : 'Test link',
            'source_link' : 'Test source link',
        }

        return licence


    def create_app_theme_image(self):
        
        image_file = SimpleUploadedFile(name='app-background.jpg',
                            content=open(TEST_BACKGROUND_IMAGE_PATH, 'rb').read(), content_type='image/jpeg')
        
        app_theme_image = AppThemeImage(self.meta_app, self.image_type, image_file=image_file)
        app_theme_image.save()

        return app_theme_image


    def get_image(self):
        image = SimpleUploadedFile(name='app-background.jpg',
                                   content=open(TEST_BACKGROUND_IMAGE_PATH, 'rb').read(),
                                   content_type='image/jpeg')

        return image
    
        
    def get_post_form_data(self):
        
        md5_image = self.get_image()
        correct_md5 = hashlib.md5(md5_image.read()).hexdigest()
        
        post_data = {
            'image_type' : self.image_type,
        }

        file_data = {
            'source_image' : self.get_image(),
        }

        licencing_data = self.get_licencing_post_data()
        post_data.update(licencing_data)

        return post_data, file_data

    
class TestManageAppThemeImage(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                    WithMetaApp, WithAppThemeImage, WithImageStore, WithMedia, WithFormTest, TenantTestCase):

    url_name = 'manage_app_theme_image'
    view_class = ManageAppThemeImage
    image_type = 'app_background'

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'image_type' : self.image_type,
        }
        return url_kwargs

    @test_settings
    def test_set_app_theme_image(self):
        view = self.get_view()
        view.set_app_theme_image(**view.kwargs)

        self.assertEqual(view.meta_app, self.meta_app)
        self.assertEqual(view.image_type, self.image_type)
        self.assertEqual(view.app_theme_image.__class__, AppThemeImage)
        

    @test_settings
    def test_get_licencing_initial(self):

        self.create_public_domain()

        app_theme_image = self.create_app_theme_image()
        view = self.get_view()
        view.set_app_theme_image(**view.kwargs)
        
        # no licence
        licencing_initial = view.get_licencing_initial()
        self.assertEqual(licencing_initial, {})

        # store a licence
        licence = self.get_licence_as_dict()
        app_theme_image.set_licence(licence)
        app_theme_image.save()

        view_2 = self.get_view()
        view_2.set_app_theme_image(**view_2.kwargs)
        
        # no licence
        licencing_initial_2 = view_2.get_licencing_initial()

        self.assertEqual(licencing_initial_2['creator_name'], licence['creator_name'])
        self.assertEqual(licencing_initial_2['creator_link'], licence['creator_link'])
        self.assertEqual(licencing_initial_2['source_link'], licence['source_link'])
        self.assertEqual(licencing_initial_2['licence'].short_name, 'CC0')
        

    @test_settings
    def test_get_form_kwargs(self):

        self.create_public_domain()

        app_theme_image = self.create_app_theme_image()
        view = self.get_view()
        view.set_app_theme_image(**view.kwargs)

        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['current_image'], app_theme_image)


    @test_settings
    def test_get_form(self):

        self.create_public_domain()

        app_theme_image = self.create_app_theme_image()
        view = self.get_view()
        view.set_app_theme_image(**view.kwargs)
        view.meta_app = self.meta_app

        form = view.get_form()
        self.assertEqual(form.__class__, AppThemeImageForm)
        

    @test_settings
    def test_get_context_data(self):

        self.create_public_domain()

        app_theme_image = self.create_app_theme_image()
        view = self.get_view()
        view.set_app_theme_image(**view.kwargs)
        view.meta_app = self.meta_app

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['image_type'], self.image_type)
        self.assertIn('image_name', context)

    '''
    post data
    '''    

    @test_settings
    def test_form_valid(self):

        # no image present
        self.create_public_domain()

        view = self.get_view()
        view.set_app_theme_image(**view.kwargs)
        view.meta_app = self.meta_app
        
        post_data, file_data = self.get_post_form_data()

        # test form with file
        form = AppThemeImageForm(self.meta_app, data=post_data, files=file_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        app_theme_image = AppThemeImage(self.meta_app, self.image_type)
        self.assertFalse(app_theme_image.exists())
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        
        
        self.assertTrue(app_theme_image.exists())


class TestDeleteAppThemeImage(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                    WithMetaApp, WithImageStore, WithMedia, WithFormTest, WithAppThemeImage, TenantTestCase):

    url_name = 'delete_app_theme_image'
    view_class = DeleteAppThemeImage
    image_type = 'app_background'

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'image_type' : self.image_type,
        }
        return url_kwargs

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.meta_app = self.meta_app
        view.image_type = self.image_type

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['image_type'], self.image_type)
        self.assertIn('verbose_name', context)
        self.assertIn('url', context)

    @test_settings
    def test_post(self):
        self.create_public_domain()

        app_theme_image = self.create_app_theme_image()

        self.assertTrue(app_theme_image.exists())

        view = self.get_view()
        view.meta_app = self.meta_app
        view.image_type = self.image_type

        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['deleted'], True)
        self.assertFalse(app_theme_image.exists())


class TestGetAppThemeImageFormField(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                            WithTenantClient, WithMetaApp, WithFormTest, WithAppThemeImage, TenantTestCase):

    url_name = 'get_app_theme_image_formfield'
    view_class = GetAppThemeImageFormField
    image_type = 'app_background'

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'image_type' : self.image_type,
        }
        return url_kwargs

    @test_settings
    def test_get_form(self):

        view = self.get_view()
        view.meta_app = self.meta_app
        view.image_type = self.image_type
        form = view.get_form()
        self.assertIn(self.image_type, form.fields)


'''
    no GET method, only POST
'''
class TestStoreObjectOrder(ViewTestMixin, WithLoggedInUser, WithUser, WithTenantClient,
                           WithMetaApp, WithFormTest, TenantTestCase):

    url_name = 'store_object_order'
    view_class = StoreObjectOrder 

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(GenericFieldToGenericForm)
        self.create_all_generic_contents(self.meta_app)
        self.link = self.get_generic_content_link(GenericForm)
        self.generic_form = self.link.generic_content

        self.field_links = []

        # create a few fields
        for i in range(1, 5):

            generic_field = GenericField(
                field_class = 'CharField',
                render_as = 'TextInput',
                label = 'Field {0}'.format(i),
            )

            generic_field.save(self.generic_form)

            fieldlink = GenericFieldToGenericForm(
                generic_form = self.generic_form,
                generic_field = generic_field,
                position = i,
            )

            fieldlink.save()
            
            self.field_links.append(fieldlink)

    def get_url_kwargs(self):
        url_kwargs = {
            'content_type_id' : self.content_type.id,
        }
        return url_kwargs

    @test_settings
    def test_post(self):

        order = [link.id for link in self.field_links]
        self.assertEqual(order, [1,2,3,4])

        for index, link in enumerate(self.field_links, 1):
            order_index = order.index(link.id)
            self.assertEqual(link.position, order_index + 1)
            
        order.reverse()
        self.assertEqual(order, [4,3,2,1])

        data = {
            'order' : json.dumps(order),
        }

        url = self.get_url()
        
        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        self.make_user_tenant_admin(self.user, self.tenant)
        response = self.tenant_client.post(url, data, **url_kwargs)
        
        self.assertEqual(response.status_code, 200)
        field_links = GenericFieldToGenericForm.objects.filter(generic_form = self.generic_form).order_by(
            'position')
        
        new_order = [link.id for link in field_links]
        self.assertEqual(new_order, order)


class TestMockButton(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                     TenantTestCase):

    url_name = 'mockbutton'
    view_class = MockButton

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.request.GET = {}
        context_data = view.get_context_data(**view.kwargs)
        self.assertIn('message', context_data)

        test_message = 'test message'
        view.request.GET = {
            'message' : test_message
        }
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['message'], test_message)

        

class TestManageAppDesign(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithTenantClient,
                          WithMetaApp, WithFormTest, TenantTestCase):

    url_name = 'manage_app_design'
    view_class = ManageAppDesign

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }
        return url_kwargs

    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view

    @test_settings
    def test_get_form(self):
        view = self.get_view()
        form = view.get_form()
        self.assertEqual(form.__class__, AppDesignForm)

    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        initial = view.get_initial()

        legal_notice = {
             'key1' : 'value1',
             'key2' : 'value2',
        }

        self.meta_app.global_options = {
            'legal_notice' : legal_notice
        }

        initial = view.get_initial()
        for key, value in legal_notice.items():
            self.assertEqual(initial[key], value)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['generic_content'], self.meta_app)
        content_type = ContentType.objects.get_for_model(MetaApp)
        self.assertEqual(context['content_type'], content_type)

    @test_settings
    def test_get(self):

        view = self.get_view()
        response = view.get(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)

        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest',
        }

        self.make_user_tenant_admin(self.user, self.tenant)
        ajax_response = self.tenant_client.get(self.get_url(), **url_kwargs)
        self.assertEqual(ajax_response.status_code, 200)

    
    @test_settings
    def test_form_valid(self):

        post_data = {
            'entity_name' : 'sisol systems',
            'street' : 'Test street 4',
            'zip_code' : 'e115bl',
            'city' : 'Munich',
            'country' :'DE',
            'email' : 'tester@test.org',
            'phone' : '+499154660679',
        }

        legal_fields = post_data.copy()


        theme = self.meta_app.get_theme()

        post_data['theme'] = theme.name
        post_data['input_language'] = self.meta_app.primary_language

        for key, value in theme.user_content['texts'].items():
            post_data[key] = '{0} test'.format(key)
            app_text = AppThemeText(self.meta_app, key)
            self.assertFalse(app_text.exists())
        

        form = AppDesignForm(self.meta_app, data=post_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)

        for key, value in theme.user_content['texts'].items():
            app_text = AppThemeText(self.meta_app, key)
            self.assertTrue(app_text.exists())

        self.meta_app.refresh_from_db()
        for key, value in legal_fields.items():
            self.assertEqual(self.meta_app.global_options['legal_notice'][key], value)


'''
    test postponed until zip is specified
'''
class TestImportFromZip(ViewTestMixin, WithLoggedInUser, WithUser, WithTenantClient,
                          WithMetaApp, WithFormTest, TenantTestCase):

    pass


class TestIdentityMixin(ViewTestMixin, WithUser, WithTenantClient, TenantTestCase):

    url_name = 'legal_notice'
    view_class = LegalNotice

    @test_settings
    def test_get_context_data(self):
        self.user = self.create_user()
        view = self.get_view()
        context = view.get_context_data()
        self.assertIn('identity', context)

        
class TestLegalNotice(ViewTestMixin, WithUser, WithTenantClient, TenantTestCase):

    url_name = 'legal_notice'
    view_class = LegalNotice

    @test_settings
    def test_dispatch(self):
        
        url = self.get_url()
        
        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        response = self.tenant_client.get(url, **url_kwargs)
        self.assertEqual(response.status_code, 200)

        response_2 = self.tenant_client.get(url)
        self.assertEqual(response_2.status_code, 200)



class TestPrivacyStatement(ViewTestMixin, WithUser, WithTenantClient, TenantTestCase):
    
    url_name = 'privacy_statement'
    view_class = PrivacyStatement

    @test_settings
    def test_dispatch(self):
        
        url = self.get_url()
        
        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        response = self.tenant_client.get(url, **url_kwargs)
        self.assertEqual(response.status_code, 200)

        response_2 = self.tenant_client.get(url)
        self.assertEqual(response_2.status_code, 200)
    

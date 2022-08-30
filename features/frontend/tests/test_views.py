from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings

from app_kit.appbuilder import AppBuilder

from app_kit.tests.mixins import (WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithFormTest, ViewTestMixin, WithImageStore, WithMedia)

from app_kit.features.frontend.views import FrontendSettingsMixin, ManageFrontend, ManageFrontendSettings

from app_kit.features.frontend.forms import FrontendSettingsForm

from app_kit.features.frontend.models import FrontendText

from .test_models import WithFrontend


# ManageFrontendSettings uses all methods of FrontendSettingsMixin
# ManageFrontend overrides some of the methods of FrontendSettingsMixin
class TestFrontendSettingsMixin(WithFrontend, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                                WithTenantClient, TenantTestCase):


    url_name = 'manage_frontend_settings'
    view_class = ManageFrontendSettings


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'frontend_id' : self.frontend.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.frontend = self.frontend
        return view

    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        view.set_frontend(**view.kwargs)

        form = view.get_form()

        self.assertEqual(form.__class__, FrontendSettingsForm)


    @test_settings
    def test_get_form_args(self):
        
        view = self.get_view()
        view.set_frontend(**view.kwargs)

        expected_form_args = [self.meta_app, self.frontend]

        form_args = view.get_form_args()

        self.assertEqual(expected_form_args, form_args)


    @test_settings
    def test_get_frontend_settings(self):
        
        view = self.get_view()
        view.set_frontend(**view.kwargs)

        frontend_settings = view.get_frontend_settings()

        self.assertEqual(frontend_settings['frontend'], 'Flat')


    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.set_frontend(**view.kwargs)

        context = view.get_context_data(**view.kwargs)

        app_builder = AppBuilder(self.meta_app)
        frontend_settings = app_builder._get_frontend_settings()

        self.assertEqual(context['frontend'], self.frontend)
        self.assertEqual(context['frontend_settings'], frontend_settings)
        self.assertEqual(context['success'], False)


    @test_settings
    def test_get_text_types(self):
        
        view = self.get_view()
        view.set_frontend(**view.kwargs)

        text_types = view.get_text_types()

        app_builder = AppBuilder(self.meta_app)
        frontend_settings = app_builder._get_frontend_settings()

        self.assertIn('legal_notice', text_types)

        for text_type in text_types:
            if text_type != 'legal_notice':
                self.assertIn(text_type, frontend_settings['userContent']['texts'])


    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        view.set_frontend(**view.kwargs)

        initial = view.get_initial()

        self.assertEqual(initial, {})

        # store some texts in the db
        app_builder = AppBuilder(self.meta_app)
        frontend_settings = app_builder._get_frontend_settings()

        for text_type, definition in frontend_settings['userContent']['texts'].items():

            frontend_text = FrontendText(
                frontend = self.frontend,
                frontend_name = self.frontend.frontend_name,
                identifier = text_type,
                text = text_type,
            )

            frontend_text.save()

        frontend_texts = FrontendText.objects.filter(frontend=self.frontend, frontend_name=self.frontend.frontend_name)
        self.assertTrue(frontend_texts.count() > 0)

        initial = view.get_initial()

        for text in frontend_texts:
            self.assertIn(text.identifier, initial)


class TestManageFrontend(WithFrontend, ViewTestMixin, WithAdminOnly, WithUser, WithLoggedInUser,
                                WithTenantClient, TenantTestCase):


    url_name = 'manage_frontend'
    view_class = ManageFrontend


    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.frontend.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.generic_content_type = self.content_type
        view.generic_content = self.frontend
        return view

    @test_settings
    def test_get_form(self):
        
        view = self.get_view()

        form = view.get_form()
        self.assertEqual(form.__class__, FrontendSettingsForm)


    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()

        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['frontend_settings_form'].__class__, FrontendSettingsForm)



class TestManageFrontendSettings(WithFrontend, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                                WithTenantClient, TenantTestCase):


    url_name = 'manage_frontend_settings'
    view_class = ManageFrontendSettings


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'frontend_id' : self.frontend.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.frontend = self.frontend
        return view


    @test_settings
    def test_set_frontend(self):
        
        view = super().get_view()
        view.set_frontend(**view.kwargs)

        self.assertEqual(view.generic_content, self.frontend)
        self.assertEqual(view.frontend, self.frontend)
        self.assertEqual(view.content_type, self.content_type)


    @test_settings
    def test_from_valid(self):

        app_builder = AppBuilder(self.meta_app)
        frontend_settings = app_builder._get_frontend_settings()

        # create data and avalid form, pass it to view.form_valid(form)
        data = {
            'legal_notice' : 'test legal notice',
        }

        for text_type, definition in frontend_settings['userContent']['texts'].items():

            data[text_type] = text_type

        
        view = self.get_view()
        view.set_frontend(**view.kwargs)

        form = FrontendSettingsForm(self.meta_app, self.frontend, data=data)

        form.is_valid()

        self.assertEqual(form.errors, {})

        response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)

        for text_type, text_content in data.items():

            frontend_text = FrontendText.objects.filter(frontend=self.frontend, frontend_name=self.frontend.frontend_name,
                identifier=text_type)

            self.assertTrue(frontend_text.exists())

            frontend_text = frontend_text.first()
            self.assertEqual(frontend_text.text, text_content)

        # test overwrite
        data_2 = {
            'legal_notice' : 'test legal notice edited',
        }

        form_2 = FrontendSettingsForm(self.meta_app, self.frontend, data=data_2)

        form_2.is_valid()

        self.assertEqual(form_2.errors, {})

        response_2 = view.form_valid(form_2)
        self.assertEqual(response_2.status_code, 200)

        ln_text = FrontendText.objects.get(frontend=self.frontend, frontend_name=self.frontend.frontend_name,
                identifier='legal_notice')

        self.assertEqual(ln_text.text, data_2['legal_notice'])
        


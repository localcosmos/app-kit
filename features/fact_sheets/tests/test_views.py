from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django_tenants.test.cases import TenantTestCase
from django.test import RequestFactory

from app_kit.features.fact_sheets.views import (ManageFactSheets, CreateFactSheet, GetFactSheetPreview,
            ManageFactSheet, ManageFactSheetImage, DeleteFactSheetImage, GetFactSheetFormFields,
            UploadFactSheetTemplate)

from app_kit.features.fact_sheets.models import FactSheet, FactSheetTemplates
from app_kit.features.fact_sheets.forms import (CreateFactSheetForm, ManageFactSheetForm, 
                                                UploadFactSheetTemplateForm)

from app_kit.features.fact_sheets.tests.common import WithFactSheets

from app_kit.tests.common import test_settings, TEST_TEMPLATE_PATH

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithImageStore, ViewTestMixin, WithMedia, MultipleURLSViewTestMixin)


from app_kit.models import ContentImage
from django.contrib.contenttypes.models import ContentType


import io


class TestManageFactSheets(WithFactSheets, ViewTestMixin, WithAdminOnly, WithUser, WithLoggedInUser,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_factsheets'
    view_class = ManageFactSheets


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
        view.generic_content_type = self.content_type
        view.generic_content = self.generic_content

        return view

    @test_settings
    def test_get_context_data(self):

        self.build_preview_app()

        view = self.get_view()
        context_data = view.get_context_data(**view.kwargs)

        fact_sheets = FactSheet.objects.filter(fact_sheets=self.generic_content)
        self.assertEqual(context_data['fact_sheets'].count(), fact_sheets.count())


class TestCreateFactSheet(WithFactSheets, ViewTestMixin, WithAdminOnly, WithUser, WithLoggedInUser,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'create_factsheet'
    view_class = CreateFactSheet

    def before_test_dispatch(self):
        self.build_preview_app()


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'fact_sheets_id' : self.generic_content.id,
        }

        return url_kwargs

    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.generic_content = self.generic_content

        return view


    @test_settings
    def test_get_context_data(self):

        self.build_preview_app()

        view = self.get_view()
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['generic_content'], self.generic_content)
        

    @test_settings
    def test_get_form(self):

        self.build_preview_app()

        view = self.get_view()
        form = view.get_form()
        self.assertTrue(isinstance(form, CreateFactSheetForm))

    @test_settings
    def test_get_initial(self):

        self.build_preview_app()

        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial['input_language'], self.generic_content.primary_language)

    @test_settings
    def test_form_valid(self):

        self.build_preview_app()

        view = self.get_view()

        post_data = {
            'title' : 'Neobiota',
            'navigation_link_name' : 'Neobiota link',
            'input_language' : 'en',
            'template_name' : 'test.html',
        }
    
        form = CreateFactSheetForm(self.meta_app, self.generic_content, data=post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/app-kit/fact-sheets/manage-factsheet/', response.url)



class WithFactSheet:

    contents = {
        'simple_content' : 'abcd',
        'layout_1' : '<b>bold</b>',
    }

    def setUp(self):
        super().setUp()

        self.fact_sheet = FactSheet(
            fact_sheets = self.generic_content,
            template_name = 'test.html',
            title = 'Neobiota',
            navigation_link_name = 'Neobiota link name',
            contents = self.contents,
        )

        self.fact_sheet.save()

        self.create_public_domain()

    def before_test_dispatch(self):
        self.build_preview_app()

    def create_fact_sheet_image(self):
        fact_sheet_content_type = ContentType.objects.get_for_model(FactSheet)
        image_store = self.create_image_store()
        
        fact_sheet_image = ContentImage(
            image_store = image_store,
            content_type = fact_sheet_content_type,
            object_id = self.fact_sheet.id,
            image_type = 'test_image',
        )

        fact_sheet_image.save()

        return fact_sheet_image
        
        
class TestManageFactSheet(WithFactSheet, WithFactSheets, ViewTestMixin, WithAdminOnly, WithUser,
                          WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_factsheet'
    view_class = ManageFactSheet


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'fact_sheet_id' : self.fact_sheet.id,
        }

        return url_kwargs

    def get_view(self):

        view = super().get_view()
        view.meta_app = self.meta_app
        view.fact_sheet = self.fact_sheet

        return view


    @test_settings
    def test_get_intial(self):

        self.build_preview_app()

        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial['title'], 'Neobiota')
        self.assertEqual(initial['navigation_link_name'], 'Neobiota link name')
        self.assertEqual(initial['input_language'], self.generic_content.primary_language)

        for key, value in self.contents.items():
            self.assertEqual(initial[key], value)
    

    @test_settings
    def test_get_form(self):

        self.build_preview_app()

        view = self.get_view()
        form = view.get_form()
        self.assertTrue(isinstance(form, ManageFactSheetForm))

        self.assertIn('simple_content', form.fields)

    @test_settings
    def test_get_preview_url(self):

        self.build_preview_app()

        view = self.get_view()
        url = view.get_preview_url()

        expected_url = 'http://test.org/apps/testmetaapp/preview/www/#/fact-sheet/neobiota-{0}/?meta_app_id={1}'.format(
            self.fact_sheet.id, self.meta_app.id)

        self.assertEqual(url, expected_url)


    @test_settings
    def test_get_context_data(self):

        self.build_preview_app()

        expected_url = 'http://test.org/apps/testmetaapp/preview/www/#/fact-sheet/neobiota-{0}/?meta_app_id={1}'.format(
            self.fact_sheet.id, self.meta_app.id)

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['fact_sheet'], self.fact_sheet)
        self.assertEqual(context['preview_url'], expected_url)


    @test_settings
    def test_form_valid(self):

        self.build_preview_app()

        view = self.get_view()

        post_data = view.get_initial()
        simple_content = 'Test simple content'
        post_data['simple_content'] = simple_content

        form = ManageFactSheetForm(self.meta_app, self.fact_sheet, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        view.form_valid(form)
        


class TestGetFactSheetPreview(WithFactSheet, WithFactSheets, ViewTestMixin, WithUser,
                          WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'fact_sheet_preview'
    view_class = GetFactSheetPreview


    def get_url_kwargs(self):
        url_kwargs = {
            'slug' : self.fact_sheet.slug,
            'meta_app_id' : self.meta_app.id,
        }

        return url_kwargs
    
    @test_settings
    def test_set_factsheet(self):

        self.build_preview_app()

        view = self.get_view()
        view.set_factsheet(**view.kwargs)
        self.assertEqual(view.fact_sheet, self.fact_sheet)
        self.assertEqual(view.meta_app, self.meta_app)
        

    @test_settings
    def test_get_context_data(self):

        self.build_preview_app()

        view = self.get_view()
        view.set_factsheet(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertIn('html', context)


class TestGetFactSheetFormFields(WithFactSheet, WithFactSheets, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                                WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'get_factsheet_form_fields'
    view_class = GetFactSheetFormFields


    def get_url_kwargs(self):
        url_kwargs = {
            'fact_sheet_id' : self.fact_sheet.id,
            'microcontent_category' : 'microcontent',
            'microcontent_type' : 'simple_content',
        }

        return url_kwargs


    @test_settings
    def test_set_content(self):

        view = self.get_view()
        view.set_content(**view.kwargs)
        self.assertEqual(view.fact_sheet, self.fact_sheet)
        self.assertEqual(view.microcontent_category, 'microcontent')
        self.assertEqual(view.microcontent_type, 'simple_content')
        

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.set_content(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['fact_sheet'], self.fact_sheet)
        

    @test_settings
    def test_get_form(self):

        view = self.get_view()
        view.set_content(**view.kwargs)

        form = view.get_form()
        



class TestUploadFactSheetTemplate(WithFactSheets, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'upload_factsheet_template'
    view_class = UploadFactSheetTemplate


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'fact_sheets_id' : self.fact_sheets.id,
        }

        return url_kwargs


    def get_view(self):

        view = super().get_view()
        view.fact_sheets = self.fact_sheets
        view.meta_app = self.meta_app

        return view


    def get_template_file(self, filename='test_template.html'):

        file_io = io.StringIO('<div>test</div>')

        memory_file = InMemoryUploadedFile(
            file_io, None, filename, 'text/html', len(file_io.getvalue()), None
        )

        return memory_file


    @test_settings
    def test_get_form(self):

        view = self.get_view()
        form = view.get_form()
        self.assertEqual(form.__class__, UploadFactSheetTemplateForm)

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['fact_sheets'], self.fact_sheets)
        self.assertFalse(context['success'])

    @test_settings
    def test_form_valid(self):

        post_data = {
            'name' : 'Test template',
            'overwrite_existing_template' : True,
        }

        file_data = {
            'template' : self.get_template_file(),
        }

        form = UploadFactSheetTemplateForm(self.fact_sheets, data=post_data, files=file_data)
        form.is_valid()

        self.assertEqual(form.errors, {})

        view = self.get_view()
        response = view.form_valid(form)

        template = FactSheetTemplates.objects.first()
        self.assertEqual(template.name, post_data['name'])
        self.assertEqual(template.template.name, 'fact_sheets/templates/2/test_template.html')

        self.assertTrue(response.context_data['success'])


class TestManageFactSheetImage(WithFactSheet, WithFactSheets, WithMedia, WithImageStore, MultipleURLSViewTestMixin,
        WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_factsheet_image'
    view_class = ManageFactSheetImage

    microcontent_category = 'image'


    def setUp(self):
        super().setUp()
        self.fact_sheet_image = self.create_fact_sheet_image()


    def get_url_kwargs_list(self):

        fact_sheet_content_type = ContentType.objects.get_for_model(FactSheet)
        
        url_kwargs_list = [
            {
                'fact_sheet_id' : self.fact_sheet.id,
                'microcontent_category' : self.microcontent_category,
                'content_image_id' : self.fact_sheet_image.id,
            },
            {
                'fact_sheet_id' : self.fact_sheet.id,
                'microcontent_category' : self.microcontent_category,
                'content_type_id' : fact_sheet_content_type.id,
                'object_id' : self.fact_sheet.id,
                'image_type' : self.fact_sheet_image.image_type,
            }
        ]

        return url_kwargs_list


    def get_views(self):

        views = super().get_views()

        for view in views:
            view.set_fact_sheet(**view.kwargs)

        return views


    @test_settings
    def test_set_fact_sheet(self):
        
        views = super().get_views()

        for view in views:

            self.assertFalse(hasattr(view, 'fact_sheet'))
            self.assertFalse(hasattr(view, 'microcontent_category'))

            view.set_content_image(*[], **view.kwargs)
            view.set_fact_sheet(**view.kwargs)

            self.assertEqual(view.fact_sheet, self.fact_sheet)
            self.assertEqual(view.microcontent_category, self.microcontent_category)


    @test_settings
    def test_get_context_data(self):

        views = self.get_views()

        for view in views:

            view.set_content_image(*[], **view.kwargs)
            view.set_licence_registry_entry(self.fact_sheet_image.image_store, 'image')
            view.set_fact_sheet(**view.kwargs)
            view.taxon = None

            context = view.get_context_data(**view.kwargs)

            self.assertEqual(context['fact_sheet'], self.fact_sheet)
            self.assertEqual(context['microcontent_category'], self.microcontent_category)
            self.assertEqual(context['microcontent_type'], self.fact_sheet_image.image_type)


class TestManageFactSheetImageMulti(TestManageFactSheetImage):

    microcontent_category = 'images'



class TestDeleteFactSheetImage(WithFactSheet, WithFactSheets, WithMedia, WithImageStore, ViewTestMixin, WithAjaxAdminOnly,
                    WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_factsheet_image'
    view_class = DeleteFactSheetImage

    microcontent_category = 'image'

    def setUp(self):
        super().setUp()
        self.fact_sheet_image = self.create_fact_sheet_image()


    def get_url_kwargs(self):
        url_kwargs = {
            'fact_sheet_id' : self.fact_sheet.id,
            'microcontent_category' : self.microcontent_category,
            'pk' : self.fact_sheet_image.id,
        }

        return url_kwargs


    def get_view(self):

        view = super().get_view()
        view.set_fact_sheet(**view.kwargs)


        return view


    @test_settings
    def test_set_fact_sheet(self):
        
        view = super().get_view()

        self.assertFalse(hasattr(view, 'fact_sheet'))
        self.assertFalse(hasattr(view, 'microcontent_category'))

        view.set_fact_sheet(**view.kwargs)
        self.assertEqual(view.fact_sheet, self.fact_sheet)
        self.assertEqual(view.microcontent_category, self.microcontent_category)


    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()

        view.set_fact_sheet(**view.kwargs)
        view.object = view.get_object()

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['fact_sheet'], self.fact_sheet)
        self.assertEqual(context['microcontent_category'], self.microcontent_category)
        self.assertEqual(context['microcontent_type'], self.fact_sheet_image.image_type)
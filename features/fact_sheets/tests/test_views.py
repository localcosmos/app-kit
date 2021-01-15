from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django_tenants.test.cases import TenantTestCase

from app_kit.features.fact_sheets.views import (ManageFactSheets, CreateFactSheet, GetFactSheetPreview,
            ManageFactSheet, UploadFactSheetImage, DeleteFactSheetImage, GetFactSheetFormField,
            UploadFactSheetTemplate)

from app_kit.features.fact_sheets.models import FactSheet, FactSheetImages, FactSheetTemplates
from app_kit.features.fact_sheets.forms import (CreateFactSheetForm, ManageFactSheetForm, 
                                                UploadFactSheetImageForm, UploadFactSheetTemplateForm)

from app_kit.features.fact_sheets.tests.common import WithFactSheets

from app_kit.tests.common import test_settings, TEST_TEMPLATE_PATH

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithFormTest, ViewTestMixin, WithMedia)


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

        view = self.get_view()
        context_data = view.get_context_data(**view.kwargs)

        fact_sheets = FactSheet.objects.filter(fact_sheets=self.generic_content)
        self.assertEqual(context_data['fact_sheets'].count(), fact_sheets.count())


class TestCreateFactSheet(WithFactSheets, ViewTestMixin, WithAdminOnly, WithUser, WithLoggedInUser,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'create_factsheet'
    view_class = CreateFactSheet


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

        view = self.get_view()
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['generic_content'], self.generic_content)
        

    @test_settings
    def test_get_form(self):

        view = self.get_view()
        form = view.get_form()
        self.assertTrue(isinstance(form, CreateFactSheetForm))

    @test_settings
    def test_get_initial(self):

        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial['input_language'], self.generic_content.primary_language)

    @test_settings
    def test_form_valid(self):

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

        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial['title'], 'Neobiota')
        self.assertEqual(initial['navigation_link_name'], 'Neobiota link name')
        self.assertEqual(initial['input_language'], self.generic_content.primary_language)

        for key, value in self.contents.items():
            self.assertEqual(initial[key], value)
    

    @test_settings
    def test_get_form(self):

        view = self.get_view()
        form = view.get_form()
        self.assertTrue(isinstance(form, ManageFactSheetForm))

        self.assertIn('simple_content', form.fields)

    @test_settings
    def test_get_preview_url(self):

        view = self.get_view()
        url = view.get_preview_url()

        expected_url = 'http://test.org/apps/testmetaapp/preview/www/#/fact-sheet/neobiota-{0}/?meta_app_id={1}'.format(
            self.fact_sheet.id, self.meta_app.id)

        self.assertEqual(url, expected_url)


    @test_settings
    def test_get_context_data(self):

        expected_url = 'http://test.org/apps/testmetaapp/preview/www/#/fact-sheet/neobiota-{0}/?meta_app_id={1}'.format(
            self.fact_sheet.id, self.meta_app.id)

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['fact_sheet'], self.fact_sheet)
        self.assertEqual(context['preview_url'], expected_url)


    @test_settings
    def test_form_valid(self):

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
        view = self.get_view()
        view.set_factsheet(**view.kwargs)
        self.assertEqual(view.fact_sheet, self.fact_sheet)
        self.assertEqual(view.meta_app, self.meta_app)
        

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_factsheet(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertIn('html', context)



class TestUploadFactSheetImageCreate(WithFactSheet, WithFactSheets, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                    WithFormTest, WithMedia, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'upload_factsheet_image'
    view_class = UploadFactSheetImage


    def get_url_kwargs(self):
        url_kwargs = {
            'fact_sheet_id' : self.fact_sheet.id,
            'microcontent_category' : 'image',
            'microcontent_type' : 'test_image',
        }

        return url_kwargs


    @test_settings
    def test_set_file(self):
        view = self.get_view()
        view.set_file(**view.kwargs)

        self.assertEqual(view.fact_sheet, self.fact_sheet)
        self.assertEqual(view.microcontent_category, 'image')
        self.assertEqual(view.microcontent_type, 'test_image')
        self.assertEqual(view.image, None)
        

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_file(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['fact_sheet'], self.fact_sheet)
        self.assertEqual(context['microcontent_category'], 'image')
        self.assertEqual(context['microcontent_type'], 'test_image')
        self.assertEqual(context['success'], False)
        self.assertEqual(context['image'], None)
    

    @test_settings
    def test_get_initial(self):

        view = self.get_view()
        view.set_file(**view.kwargs)

        initial = view.get_initial()
        self.assertFalse('source_image' in initial)


    @test_settings
    def test_get_form_kwargs(self):

        view = self.get_view()
        view.set_file(**view.kwargs)

        form_kwargs = view.get_form_kwargs()
        self.assertFalse('current_image' in form_kwargs)
        

    @test_settings
    def test_form_valid(self):

        post_data = {
            'creator_name' : 'image creator',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
            'image_type' : 'test_image',
        }

        file_data = {
            'source_image' : self.get_image('test_image.jpg'),
        }

        form = UploadFactSheetImageForm(data=post_data, files=file_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()
        view.set_file(**view.kwargs)

        response = view.form_valid(form)
        self.assertTrue(response.context_data['success'])
        self.assertEqual(response.context_data['form'].__class__, UploadFactSheetImageForm)
        self.assertEqual(response.context_data['image'], view.image)


class TestUploadFactSheetImageManage(WithFactSheet, WithFactSheets, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                               WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'manage_factsheet_image'
    view_class = UploadFactSheetImage


    def get_url_kwargs(self):
        url_kwargs = {
            'fact_sheet_id' : self.fact_sheet.id,
            'microcontent_category' : 'image',
            'microcontent_type' : 'test_image',
            'pk' : self.fact_sheet_image.pk,
        }

        return url_kwargs


    def setUp(self):
        super().setUp()

        # create the image

        self.fact_sheet_image = FactSheetImages(
            fact_sheet = self.fact_sheet,
            microcontent_type = 'test_image',
            image = self.get_image('test.jpg'),
        )

        self.fact_sheet_image.save()

    @test_settings
    def test_set_file(self):
        view = self.get_view()
        view.set_file(**view.kwargs)

        self.assertEqual(view.fact_sheet, self.fact_sheet)
        self.assertEqual(view.microcontent_category, 'image')
        self.assertEqual(view.microcontent_type, 'test_image')
        self.assertEqual(view.image, self.fact_sheet_image)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_file(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['fact_sheet'], self.fact_sheet)
        self.assertEqual(context['microcontent_category'], 'image')
        self.assertEqual(context['microcontent_type'], 'test_image')
        self.assertEqual(context['success'], False)
        self.assertEqual(context['image'], self.fact_sheet_image)


    @test_settings
    def test_get_initial(self):

        view = self.get_view()
        view.set_file(**view.kwargs)

        initial = view.get_initial()
        self.assertEqual(initial['source_image'], self.fact_sheet_image.image)


    @test_settings
    def test_get_form_kwargs(self):

        view = self.get_view()
        view.set_file(**view.kwargs)

        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['current_image'], self.fact_sheet_image)


    @test_settings
    def test_form_valid(self):

        post_data = {
            'creator_name' : 'image creator',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
            'image_type' : 'test_image',
        }

        file_data = {
            'source_image' : self.get_image('test_image_neu.jpg'),
        }

        form = UploadFactSheetImageForm(data=post_data, files=file_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()
        view.set_file(**view.kwargs)

        response = view.form_valid(form)
        self.assertTrue(response.context_data['success'])
        self.assertEqual(response.context_data['form'].__class__, UploadFactSheetImageForm)
        self.assertEqual(response.context_data['image'].pk, self.fact_sheet_image.pk)
        
        
        

class TestDeleteFactSheetImage(WithFactSheet, WithFactSheets, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                               WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_factsheet_image'
    view_class = DeleteFactSheetImage


    def get_url_kwargs(self):
        url_kwargs = {
            'pk' : self.fact_sheet_image.pk,
        }

        return url_kwargs


    def get_url(self):
        url = super().get_url()
        url = '{0}?microcontent_category=image'.format(url)
        return url


    def get_view(self):

        view = super().get_view()
        view.object = self.fact_sheet_image

        return view


    def setUp(self):
        super().setUp()

        # create the image

        self.fact_sheet_image = FactSheetImages(
            fact_sheet = self.fact_sheet,
            microcontent_type = 'test_image',
            image = self.get_image('test.jpg'),
        )

        self.fact_sheet_image.save()


    @test_settings
    def test_get_verbose_name(self):

        view = self.get_view()
        verbose_name = view.get_verbose_name()
        self.assertEqual(verbose_name, 'Test image')


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['fact_sheet'], self.fact_sheet)
        self.assertEqual(context['microcontent_type'], 'test_image')
        self.assertEqual(context['microcontent_category'], 'image')



class TestGetFactSheetFormField(WithFactSheet, WithFactSheets, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                                WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'get_factsheet_form_field'
    view_class = GetFactSheetFormField


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



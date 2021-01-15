##############################################################################################################
#
# TESTS FOR FORMS
#
##############################################################################################################

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings, TEST_TEMPLATE_PATH
from app_kit.tests.mixins import WithMetaApp, WithFormTest, WithUser, WithMedia

from app_kit.features.fact_sheets.forms import (FactSheetFormCommon, CreateFactSheetForm, ManageFactSheetForm,
                                                UploadFactSheetImageForm, UploadFactSheetTemplateForm)

from app_kit.features.fact_sheets.models import FactSheetImages, FactSheetTemplates

from app_kit.features.fact_sheets.tests.common import WithFactSheets

import io


class TestFactSheetFormCommon(WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        form = FactSheetFormCommon()

        post_data = {
            'title' : 'Neobiota',
            'navigation_link_name' : 'Neobiota link',
            'input_language' : 'en',
        }

        self.perform_form_test(FactSheetFormCommon, post_data)



class TestCreateFactSheetForm(WithFormTest, WithFactSheets, WithMetaApp, TenantTestCase):

    @test_settings
    def test_get_template_choices(self):

        form = CreateFactSheetForm(self.meta_app, self.fact_sheets)

        choices = form.get_template_choices()
        self.assertEqual(choices, [('test.html', 'test.html')])


    @test_settings
    def test_form(self):

        post_data = {
            'title' : 'Neobiota',
            'navigation_link_name' : 'Neobiota link',
            'input_language' : 'en',
            'template_name' : 'test.html',
        }

        form_args = [self.meta_app, self.fact_sheets]

        self.perform_form_test(CreateFactSheetForm, post_data, form_args=form_args)


class TestManageFactSheetForm(WithFormTest, WithFactSheets, WithMetaApp, TenantTestCase):

    @test_settings
    def test_init(self):

        fact_sheet = self.create_fact_sheet()

        form = ManageFactSheetForm(self.meta_app, fact_sheet)

        self.assertEqual(len(form.fields), 8)


    @test_settings
    def test_form(self):

        fact_sheet = self.create_fact_sheet()

        post_data = {
            'title' : 'Neobiota',
            'navigation_link_name' : 'Neobiota link',
            'input_language' : 'en',
            'simple_content' : 'test simple content',
            'layout1' : 'layoutable-full',
            'layout2' : 'layout simple',
        }

        form_args = [self.meta_app, fact_sheet]

        self.perform_form_test(ManageFactSheetForm, post_data, form_args=form_args)
        


class TestUploadFactSheetImageForm(WithFormTest, WithFactSheets, WithMetaApp, TenantTestCase):

    @test_settings
    def test_get_source_image_field(self):

        form = UploadFactSheetImageForm()
        field = form.get_source_image_field()
        self.assertEqual(field.required, True)
        self.assertEqual(field.widget.current_image, None)

    @test_settings
    def test_get_source_image_field_with_current_image(self):
        # attach current image
        fact_sheet = self.create_fact_sheet()

        filename = 'test.jpg'

        fact_sheet_image = FactSheetImages(
            fact_sheet = fact_sheet,
            microcontent_type = 'test_image',
            image = self.get_image(filename)
        )

        fact_sheet_image.save()
        
        form = UploadFactSheetImageForm(current_image = fact_sheet_image)

        field = form.get_source_image_field()
        self.assertEqual(field.required, False)
        self.assertEqual(field.widget.current_image, fact_sheet_image.image)

    @test_settings
    def test_form(self):

        image = self.get_image('test_image.jpg')

        post_data = {
            'image_type' : 'image',
            'crop_parameters' : {},
            'creator_name' : 'James Bond',
            'creator_link' : '',
            'source_link' : '',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
        }

        file_data = {
            'source_image' : self.get_image,
        }

        self.perform_form_test(UploadFactSheetImageForm, post_data, file_data=file_data)


class TestUploadFactSheetTemplateForm(WithFormTest, WithFactSheets, WithUser, WithMetaApp,
                                      WithMedia, TenantTestCase):

    def get_template_file(self, filename='test_template.html'):

        file_io = io.StringIO('<div>test</div>')

        memory_file = InMemoryUploadedFile(
            file_io, None, filename, 'text/html', len(file_io.getvalue()), None
        )

        return memory_file

    @test_settings
    def test_init(self):
         form = UploadFactSheetTemplateForm(self.fact_sheets)
         self.assertEqual(form.fact_sheets, self.fact_sheets)


    @test_settings
    def test_clean(self):

        post_data = {
            'name' : 'Test template',
            'overwrite_existing_template' : False,
        }

        form = UploadFactSheetTemplateForm(self.fact_sheets, data=post_data)

        is_valid = form.is_valid()
        self.assertIn('template', form.errors)

        # upload a non existant template
        file_data_2 = {
            'template' : self.get_template_file(),
        }

        form_2 = UploadFactSheetTemplateForm(self.fact_sheets, data=post_data, files=file_data_2)

        is_valid = form_2.is_valid()
        self.assertEqual(form_2.errors, {})


        # upload existing template, no overwrite
        filename = 'neobiota.html'

        template = SimpleUploadedFile(name=filename, content=open(TEST_TEMPLATE_PATH , 'rb').read(),
                                        content_type='text/html')

        user = self.create_user()

        fact_sheet_template = FactSheetTemplates(
            fact_sheets = self.fact_sheets,
            template = template,
            uploaded_by = user,
        )

        fact_sheet_template.save()
        
        file_data_3 = {
            'template' : self.get_template_file(filename=filename),
        }

        form_3 = UploadFactSheetTemplateForm(self.fact_sheets, data=post_data, files=file_data_3)

        is_valid = form_3.is_valid()
        self.assertFalse(is_valid)
        self.assertIn('__all__', form_3.errors)

        # upload existing, overwrite
        post_data['overwrite_existing_template'] = True
        file_data_4 = {
            'template' : self.get_template_file(filename=filename),
        }
        form_4 = UploadFactSheetTemplateForm(self.fact_sheets, data=post_data, files=file_data_4)
        self.assertEqual(form_4.errors, {})


    @test_settings
    def test_form(self):

        post_data = {
            'name' : 'Test template',
            'overwrite_existing_template' : True,
        }

        file_data = {
            'template' : self.get_template_file,
        }

        form_args = [self.fact_sheets]

        self.perform_form_test(UploadFactSheetTemplateForm, post_data, file_data=file_data, form_args=form_args)

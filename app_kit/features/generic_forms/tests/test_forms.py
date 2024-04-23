from django.test import TestCase
from django_tenants.test.cases import TenantTestCase

from django.contrib.contenttypes.models import ContentType
from django import forms

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.generic_forms.forms import (DynamicForm, DynamicField, GenericFieldForm, AddValueForm,
                                                  GenericFormChoicesMixin, GenericFormOptionsForm)

from app_kit.features.generic_forms.models import (GenericForm, GenericField, GenericFieldToGenericForm,
                        GenericValues, DEFAULT_WIDGETS, DJANGO_FIELD_CLASSES, ALLOWED_WIDGETS, NUMBER_FIELDS)

from app_kit.models import MetaAppGenericContent

import uuid


class WithGenericForm:

    def create_generic_form_with_fields(self, meta_app, create_options=True):

        form_name = 'Test Generic Form'
        generic_form = GenericForm.objects.create(form_name, meta_app.primary_language)

        # create all fields
        # create taxonfield
        taxonfield = GenericField(
            field_class='TaxonField',
            render_as=DEFAULT_WIDGETS['TaxonField'],
            role='taxonomic_reference',
            label='Taxonomic Reference',
            help_text='Taxon',
        )

        taxonfield.save(generic_form)
        taxonfield_link = GenericFieldToGenericForm(generic_form=generic_form, generic_field=taxonfield)
        taxonfield_link.save()

        # create geofield
        geofield = GenericField(
            field_class='PointJSONField',
            render_as=DEFAULT_WIDGETS['PointJSONField'],
            role='geographic_reference',
            label='Geographic Reference',
            help_text='gps',
        )

        geofield.save(generic_form)
        geofield_link = GenericFieldToGenericForm(generic_form=generic_form, generic_field=geofield)
        geofield_link.save()

        # create timefield
        timestampfield = GenericField(
            field_class='DateTimeJSONField',
            render_as=DEFAULT_WIDGETS['DateTimeJSONField'],
            role='temporal_reference',
            label='Temporal Reference',
            help_text='date and time',
        )

        timestampfield.save(generic_form)
        timestampfield_link = GenericFieldToGenericForm(generic_form=generic_form, generic_field=timestampfield)
        timestampfield_link.save()

        reference_classes = ['TaxonField', 'PointJSONField', 'DateTimeJSONField']

        for field_class, field_name in DJANGO_FIELD_CLASSES:

            if field_class not in reference_classes:

                generic_field = GenericField(
                    field_class=field_class,
                    render_as=DEFAULT_WIDGETS[field_class],
                    label=field_name,
                )

                # create options
                if create_options == True:

                    if field_class in ['DecimalField', 'Floatfield', 'IntegerField']:

                        generic_field.options = {
                            'min_value' : -4,
                            'max_value' : 5,
                            'step' : 1,
                            'unit' : 'm',
                        }

                    if field_class == 'DecimalField':
                        generic_field.options['decimal_places'] = 2

                generic_field.save(generic_form)
                field_link = GenericFieldToGenericForm(generic_form=generic_form, generic_field=generic_field)
                field_link.save()

                # create values if necessary

                if field_class == 'ChoiceField':

                    for choice in ['choice 1', 'choice 2']:

                        value = GenericValues(
                            generic_field=generic_field,
                            text_value=choice,
                            value_type='choice',
                            name=choice,
                        )

                        value.save()

                elif field_class == 'MultipleChoiceField':

                    for choice in ['muliple choice 1', 'multiple choice 2']:

                        value = GenericValues(
                            generic_field=generic_field,
                            text_value=choice,
                            value_type='choice',
                            name=choice,
                        )

                        value.save()


        return generic_form
                
                

class TestDynamicForm(WithMetaApp, WithGenericForm, TenantTestCase):

    @test_settings
    def test_init(self):

        dynamic_fields = []

        generic_form = self.create_generic_form_with_fields(self.meta_app, create_options=True)

        generic_field_links = GenericFieldToGenericForm.objects.filter(generic_form=generic_form)

        for field_link in generic_field_links:
            dynamic_field = DynamicField(field_link, generic_form.primary_language, self.meta_app)

            dynamic_fields.append(dynamic_field)

        dynamic_form = DynamicForm(dynamic_fields)
        for field_link in generic_field_links:
            self.assertIn(str(field_link.generic_field.uuid), dynamic_form.fields)


class TestDynamicField(WithMetaApp, WithGenericForm, TenantTestCase):

    @test_settings
    def test_init(self):

        generic_form = self.create_generic_form_with_fields(self.meta_app, create_options=True)
        generic_field_links = GenericFieldToGenericForm.objects.filter(generic_form=generic_form)

        for field_link in generic_field_links:
            generic_field = field_link.generic_field
            dynamic_field = DynamicField(field_link, generic_form.primary_language, self.meta_app)

            self.assertEqual(str(dynamic_field.uuid), str(generic_field.uuid))

            if generic_field.field_class in ['DecimalField', 'IntegerField', 'FloatField']:
                unit = generic_field.get_option('unit')
                if unit:
                    label = '{0} ({1})'.format(generic_field.label, unit)
                else:
                    label = generic_field.label
                self.assertEqual(dynamic_field.django_field.label, label)
            else:
                self.assertEqual(dynamic_field.django_field.label, generic_field.label)

            if generic_field.field_class in ['ChoiceField', 'MultipleChoiceField']:

                choices = generic_field.choices()

                expected_choices_count = len(choices)
                if generic_field.field_class == 'ChoiceField' and field_link.is_required == False:
                    expected_choices_count = len(choices) + 1
                
                self.assertEqual(len(dynamic_field.django_field.choices), expected_choices_count)

                for choice in choices:
                    if choice.is_default:
                        self.assertEqual(dynamic_field.django_field.initial, choice.text_value)        
    


class TestGenericFieldForm(TenantTestCase):

    @test_settings
    def test_init(self):

        generic_field_class = 'CharField'

        # test field_class as data
        data = {
            'generic_field_class' : generic_field_class,
        }

        form = GenericFieldForm(data=data)
        self.assertEqual(len(form.fields['widget'].choices), len(ALLOWED_WIDGETS[generic_field_class]))

        # test field_class as initial
        form_2 = GenericFieldForm(initial=data)
        self.assertEqual(len(form.fields['widget'].choices), len(ALLOWED_WIDGETS[generic_field_class]))


    @test_settings
    def test_clean_is_required(self):

        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'is_required' : False,
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data
            
            is_required = form.clean_is_required()
            self.assertFalse(is_required)

        # test is_required == True
        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'is_required' : True,
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            if generic_field_class == 'MultipleChoiceField':
                with self.assertRaises(forms.ValidationError):
                    is_required = form.clean_is_required()

            else:
                is_required = form.clean_is_required()
                self.assertTrue(is_required)
            

    @test_settings
    def test_clean_max_value(self):

        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'max_value' : 'a',
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            with self.assertRaises(forms.ValidationError):
                max_value = form.clean_max_value()

        # check integer value
        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            max_value = '1'

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'max_value' : max_value,
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            if generic_field_class not in NUMBER_FIELDS:
                with self.assertRaises(forms.ValidationError):
                    cleaned_max_value = form.clean_max_value()

            else:
                cleaned_max_value = form.clean_max_value()
                self.assertEqual(max_value, cleaned_max_value)

        # check float value
        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            max_value = '1.4'

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'max_value' : max_value,
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            if generic_field_class not in NUMBER_FIELDS or generic_field_class == 'IntegerField':
                with self.assertRaises(forms.ValidationError):
                    cleaned_max_value = form.clean_max_value()

            else:
                cleaned_max_value = form.clean_max_value()
                self.assertEqual(max_value, cleaned_max_value)
                

    @test_settings
    def test_clean_min_value(self):

        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'min_value' : 'a',
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            with self.assertRaises(forms.ValidationError):
                min_value = form.clean_min_value()

        # check integer value
        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            min_value = '1'

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'min_value' : min_value,
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            if generic_field_class not in NUMBER_FIELDS:
                with self.assertRaises(forms.ValidationError):
                    cleaned_min_value = form.clean_min_value()

            else:
                cleaned_min_value = form.clean_min_value()
                self.assertEqual(min_value, cleaned_min_value)

        # check float value
        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            min_value = '1.4'

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'min_value' : min_value,
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            if generic_field_class not in NUMBER_FIELDS or generic_field_class == 'IntegerField':
                with self.assertRaises(forms.ValidationError):
                    cleaned_min_value = form.clean_min_value()

            else:
                cleaned_min_value = form.clean_min_value()
                self.assertEqual(min_value, cleaned_min_value)

    @test_settings
    def test_clean_decimal_places(self):

        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            decimal_places = '1.5'

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'decimal_places' : decimal_places,
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            with self.assertRaises(forms.ValidationError):
                cleaned_decimal_places = form.clean_decimal_places()


        # valid input
        for generic_field_class, field_name in DJANGO_FIELD_CLASSES:

            decimal_places = '2'

            cleaned_data = {
                'generic_field_class' : generic_field_class,
                'decimal_places' : decimal_places,
            }

            form = GenericFieldForm(data=cleaned_data)
            form.cleaned_data = cleaned_data

            if generic_field_class != 'DecimalField':
                with self.assertRaises(forms.ValidationError):
                    cleaned_decimal_places = form.clean_decimal_places()

            else:
                cleaned_decimal_places = form.clean_decimal_places()
                self.assertEqual(cleaned_decimal_places, int(decimal_places))
    

class TestAddValueForm(WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        form = AddValueForm()

        post_data = {
            'generic_field_id' : 1,
            'generic_value_type' : 'choice',
            'value' : 'test choice'
        }


        self.perform_form_test(AddValueForm, post_data)


# a form for testing GenericFormChoicesMixin
class SelectGenericForm(GenericFormChoicesMixin, forms.Form):

    generic_form = forms.ChoiceField()
    generic_form_choicefield = 'generic_form'

    uuid_to_instance = {}

    
class TestGenericFormChoicesMixin(WithMetaApp, WithGenericForm, TenantTestCase):

    @test_settings
    def test_load_generic_form_choices(self):

        generic_form = self.create_generic_form_with_fields(self.meta_app, create_options=True)
        generic_form_link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(GenericForm),
            object_id=generic_form.id,
        )
        generic_form_link.save()

        select_form = SelectGenericForm
        select_form.meta_app = self.meta_app

        form = select_form()

        self.assertEqual(len(form.fields['generic_form'].choices), 2)
        self.assertEqual(form.fields['generic_form'].choices[1][0], str(generic_form.uuid))
        self.assertEqual(form.fields['generic_form'].choices[1][1], generic_form.name)



class TestGenericFormOptionsForm(WithMetaApp,WithFormTest, WithGenericForm, TenantTestCase):

    @test_settings
    def test_form(self):

        post_data = {
            'is_default' : True,
        }

        generic_form = self.create_generic_form_with_fields(self.meta_app, create_options=True)

        form_kwargs = {
            'meta_app' : self.meta_app,
            'generic_content' : generic_form,
        }

        self.perform_form_test(GenericFormOptionsForm, post_data, form_kwargs=form_kwargs)

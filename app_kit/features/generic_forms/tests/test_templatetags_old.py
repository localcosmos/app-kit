#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.test import TestCase, RequestFactory
from django.conf import settings
from django.contrib.sites.models import Site

from django.urls import reverse
import os, json, shutil, random


from generic_forms.templatetags.genericforms import (formelement_locale, getvalue, formelement_locale_json,
                                                     fieldform_title, extractval, field, field_class, field_id,
                                                     field_name, render_field_choices)

from generic_forms.models import (Field, Form, FieldLocale, FormLocale, Values, ValueLocale, FormData,
                                  DJANGO_FIELD_WIDGETS, DJANGO_FIELD_CLASSES, DEFAULT_WIDGETS,
                                  VALUE_TYPES, FIELDCLASS_DATATYPE)

from generic_forms.forms import FormForField


class TestTemplateTags(TestCase):

    def setUp(self):

        self.test_dataset = Site(
            name = "test_client",
            domain = "domain",
        )
        self.test_dataset.save()

        self.form = Form(
            published_version = 1
        )
        self.form.save()

        
        self.formlocale = FormLocale(
            form = self.form,
            name = u"Testförm",
            locale = "en",
            is_primary = True
        )

        self.formlocale.save()

        self.created_fields = []
        self.created_field_locales = []

        # test ALL POSSIBLE FIELDS
        for cl in DJANGO_FIELD_CLASSES:
            field = Field(
                form = self.form,
                field_class = cl[0],
                render_as = DEFAULT_WIDGETS[cl[0]],
                is_required = bool(random.getrandbits(1))
            )

            field.save()

            self.created_fields.append(field)

            fieldlocale = FieldLocale(
                field = field,
                label = cl[0],
                locale = "en"
            )

            fieldlocale.save()

            self.created_field_locales.append(fieldlocale)

            # add values to those who need it
            if cl[0] in ["ChoiceField", "MultipleChoiceField"]:

                for choice in ["c1","c2","c3"]:

                    value = Values(
                        field = field,
                        text_value = choice,
                        value_type = "choice"
                    )

                    value.save()

                    locale = ValueLocale(
                        value = value,
                        locale = "en",
                        name = choice
                    )

                    locale.save()

            elif cl[0] == "DecimalField":
                value = Values(
                    field = field,
                    text_value = "2",
                    value_type = "precision"
                )
                value.save()

            elif cl[0] == "IntegerField":

                min_value = Values(
                    field = field,
                    text_value = "-5",
                    value_type = "min_value"
                )
                min_value.save()

                max_value = Values(
                    field = field,
                    text_value = "5",
                    value_type = "max_value"
                )
                max_value.save()

        self.form.dump()

        self.factory = RequestFactory()


    def tearDown(self):

        self.test_dataset.delete()

        formpath = os.path.join(settings.MEDIA_ROOT, "generic_forms", str(self.form.uuid))
        if os.path.isdir(formpath):
            shutil.rmtree(formpath)

        for loc in self.created_field_locales:
            loc.delete()

        for field in self.created_fields:
            field.delete()

        self.formlocale.delete()
        self.form.delete()

    
    def test_formelement_locale_field_exists(self):

        locale = formelement_locale(self.created_fields[0], self.form)
        label = FieldLocale.objects.get(field=self.created_fields[0]).label
        self.assertEqual(locale, label)


    def test_formelement_locale_field_fallback(self):

        label = FieldLocale.objects.get(field=self.created_fields[0])
        text = label.label
        label.locale = "fr"
        label.save()

        locale = formelement_locale(self.created_fields[0], self.form)
        self.assertEqual(locale, text)

    
    def test_formelement_locale_asObj(self):
        locale = formelement_locale(self.created_fields[0], self.form, True)
        label = FieldLocale.objects.get(field=self.created_fields[0])
        self.assertEqual(locale, label)


    def test_formelement_locale_value(self):

        value = ValueLocale.objects.all().first()
        locale = formelement_locale(value.value, self.form)

        self.assertEqual(locale, value.name)

        locale = formelement_locale(value.value, self.form, True)
        self.assertEqual(locale, value)
        

    # json dump
    def test_getvalue(self):

        form = self.form.load_json()

        for field in form["fields"]:

            if field["field_class"] == "IntegerField":

                value = getvalue(field, "min_value")
                self.assertEqual(value, str(-5))

                non_value = getvalue(field, "precision")
                self.assertEqual(non_value, None)

    
    def test_formelement_locale_json(self):
        form = self.form.load_json()

        field = form["fields"][0]

        locale = formelement_locale_json(field, "label", "en")

        self.assertEqual(field["locales"]["en"]["label"], locale)

    # assertion problematic as we get lazyobject back
    def test_fieldform_title(self):
        # unbound
        for field_class in DJANGO_FIELD_CLASSES:

            initial = {
                "field_class" : field_class[0],
                "widget" : DEFAULT_WIDGETS[field_class[0]]
            }
            form = FormForField(initial=initial)

            title = fieldform_title(form)

            form = FormForField(initial)
            self.assertTrue(form.is_bound)
            title = fieldform_title(form)

    

    def test_extractval(self):
        for field_class in DJANGO_FIELD_CLASSES:

            initial = {
                "field_class" : field_class[0],
                "widget" : DEFAULT_WIDGETS[field_class[0]],
                
            }
            form = FormForField(initial=initial)

            value = extractval(form, "field_class")
            self.assertEqual(value, field_class[0])

            form = FormForField(initial)
            self.assertTrue(form.is_bound)
            value = extractval(form, "field_class")
            self.assertEqual(value, field_class[0])

    
    def test_field(self):

        field_ = self.created_fields[0]

        initial = {
            "field_id" : field_.id
        }
        
        form = FormForField(initial=initial)

        field__ = field(form)
        self.assertEqual(field__, field_)

        form = FormForField(initial)
        self.assertTrue(form.is_bound)
        field__ = field(form)
        self.assertEqual(field__, field_)
    
    
    def test_field_class(self):
        field = self.created_fields[0]

        initial = {
            "field_class" : field.field_class
        }
        
        form = FormForField(initial=initial)

        field_class_ = field_class(form)
        self.assertEqual(field_class_, field.field_class)

        form = FormForField(initial)
        self.assertTrue(form.is_bound)
        field_class_ = field_class(form)
        self.assertEqual(field_class_, field.field_class)

    
    def test_field_id(self):
        field = self.created_fields[0]

        initial = {
            "field_id" : field.id
        }
        
        form = FormForField(initial=initial)

        field_id_ = field_id(form)
        self.assertEqual(field_id_, field.id)

        form = FormForField(initial)
        self.assertTrue(form.is_bound)
        field_id_ = field_id(form)
        self.assertEqual(field_id_, field.id)
    
    
    def test_render_field_choices(self):

        for field in self.created_fields:

            if field.field_class in ["ChoiceField", "MultipleChoiceField"]:
                dic = render_field_choices(field.id, self.form)
                self.assertEqual(len(dic.keys()), 5)
                    
    

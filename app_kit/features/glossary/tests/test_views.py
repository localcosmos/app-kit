from django.test import TestCase, RequestFactory
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithFormTest, ViewTestMixin)


from app_kit.features.glossary.views import (ManageGlossary, AddGlossaryEntry, ManageGlossaryEntry,
                                             GetGlossaryEntry, GetGlossaryEntries, DeleteGlossaryEntry)

from app_kit.features.glossary.models import Glossary, GlossaryEntry, TermSynonym

from app_kit.features.glossary.forms import GlossaryEntryForm, GlossaryEntryWithImageForm


from app_kit.models import MetaAppGenericContent

class WithGlossary:

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(Glossary)
        
        # create link
        generic_content_name = '{0} {1}'.format(self.meta_app.name, Glossary.__class__.__name__)
        self.generic_content = Glossary.objects.create(generic_content_name, self.meta_app.primary_language)

        self.link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=self.content_type,
            object_id=self.generic_content.id
        )

        self.link.save()

class TestManageGlossary(WithGlossary, ViewTestMixin, WithAdminOnly, WithUser, WithLoggedInUser, WithMetaApp,
                         WithTenantClient, TenantTestCase):

    url_name = 'manage_glossary'
    view_class = ManageGlossary

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
    def test_get_glossary_entry_form(self):

        view = self.get_view()
        form = view.get_glossary_entry_form()
        self.assertEqual(form.__class__, GlossaryEntryForm)
        self.assertEqual(form.initial['glossary'], self.generic_content)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['glossary_entry_form'].__class__, GlossaryEntryForm)
        self.assertEqual(context['glossary_entries'].count(), 0)


class TestAddGlossaryEntry(WithGlossary, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'add_glossary_entry'
    view_class = AddGlossaryEntry

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'glossary_id' : self.generic_content.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.glossary = self.generic_content
        view.meta_app = self.meta_app
        view.set_glossary_entry()
        view.set_content_image()
        return view

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['generic_content'], self.generic_content)
        self.assertEqual(context['form'].__class__, GlossaryEntryWithImageForm)


    @test_settings
    def test_set_glossary_entry(self):
        view = super().get_view()
        view.set_glossary_entry()
        self.assertEqual(view.glossary_entry, None)

    @test_settings
    def test_set_content_image(self):
        view = super().get_view()
        view.set_glossary_entry()
        view.set_content_image()
        self.assertEqual(view.content_image, None)
        self.assertEqual(view.content_instance, None)
        self.assertEqual(view.licence_registry_entry, None)
        self.assertEqual(view.image_type, None)
        self.assertEqual(view.taxon, None)
        self.assertEqual(view.object_content_type, ContentType.objects.get_for_model(GlossaryEntry))
        self.assertTrue(view.new)


    @test_settings
    def test_get_initial(self):
        view = self.get_view()

        initial = view.get_initial()
        self.assertEqual(initial['glossary'], self.generic_content)


    @test_settings
    def test_form_valid(self):
        view = self.get_view()

        view.glossary = self.generic_content

        data = {
            'input_language' : self.generic_content.primary_language,
            'glossary' : self.generic_content.id,
            'term' : 'Test term',
            'definition' : 'Test definition',
            'synonyms' : 'Test synonym 1, test synonym2',
        }
        form = GlossaryEntryForm(data=data, initial=view.get_initial(),
                                 language=self.generic_content.primary_language)

        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['saved_glossary_entry'], True)
        self.assertEqual(response.context_data['form'].is_bound, False)
        glossary_entry = GlossaryEntry.objects.all().last()
        self.assertEqual(response.context_data['glossary_entry'], glossary_entry)

        synonyms = TermSynonym.objects.filter(glossary_entry=glossary_entry)
        self.assertEqual(synonyms.count(), 2)
        synonym_terms = set(synonyms.values_list('term', flat=True))
        self.assertEqual(synonym_terms, set(['Test synonym 1', 'test synonym2']))



class WithGlossaryEntry:
    
    def setUp(self):
        super().setUp()
        self.glossary_entry = GlossaryEntry(
            glossary = self.generic_content,
            term = 'Test term',
            definition = 'Test definition',
        )

        self.glossary_entry.save()

        for term in ['syno 1', 'syno 2']:

            synonym = TermSynonym(
                glossary_entry = self.glossary_entry,
                term = term,
            )
            synonym.save()


            
class TestManageGlossaryEntry(WithGlossaryEntry, WithGlossary, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                              WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'edit_glossary_entry'
    view_class = ManageGlossaryEntry


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'glossary_id' : self.generic_content.id,
            'glossary_entry_id' : self.glossary_entry.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.glossary = self.generic_content
        view.meta_app = self.meta_app
        view.set_glossary_entry(**view.kwargs)
        view.set_content_image()
        return view

    @test_settings
    def test_get_form_kwargs(self):

        view = self.get_view()
        view.glossary_entry = self.glossary_entry

        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['instance'], self.glossary_entry)
        self.assertEqual(form_kwargs['language'], self.generic_content.primary_language)

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.glossary_entry = self.glossary_entry

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['glossary_entry'], self.glossary_entry)
        self.assertEqual(context['form'].__class__, GlossaryEntryForm)


    @test_settings
    def test_get_initial(self):

        view = self.get_view()
        view.glossary_entry = self.glossary_entry

        initial = view.get_initial()
        self.assertEqual(initial['glossary'], self.generic_content)
        self.assertEqual(initial['synonyms'], 'syno 1,syno 2')

    

class TestGetGlossaryEntries(WithGlossaryEntry, WithGlossary, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                             WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'get_glossary_entries'
    view_class = GetGlossaryEntries

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'glossary_id' : self.generic_content.id,
        }
        return url_kwargs
        

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.glossary = self.generic_content
        view.meta_app = self.meta_app

        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['generic_content'], self.generic_content)
        self.assertEqual(context['glossary_entries'].count(), 1)


class TestGetGlossaryEntry(WithGlossaryEntry, WithGlossary, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                             WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'get_glossary_entry'
    view_class = GetGlossaryEntry

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'glossary_entry_id' : self.glossary_entry.id,
        }
        return url_kwargs

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.glossary_entry = self.glossary_entry
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['glossary_entry'], self.glossary_entry)
        self.assertEqual(context['generic_content'], self.generic_content)



class TestDeleteGlossaryEntry(WithGlossaryEntry, WithGlossary, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                             WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_glossary_entry'
    view_class = DeleteGlossaryEntry

    def get_url_kwargs(self):
        url_kwargs = {
            'pk' : self.glossary_entry.id,
        }
        return url_kwargs


    @test_settings
    def test_form_valid(self):
        view = self.get_view()

        entry_pk = self.glossary_entry.pk
        query = GlossaryEntry.objects.filter(pk=entry_pk)

        self.assertTrue(query.exists())

        view.request.method = 'POST'

        response = view.post(view.request, **view.kwargs)

        self.assertFalse(query.exists())

        self.assertEqual(response.context_data['deleted'], True)
        self.assertEqual(response.context_data['glossary_entry_id'], entry_pk)


        

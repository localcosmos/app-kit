from django.views.generic import FormView, TemplateView
from django.utils.decorators import method_decorator
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.decorators import ajax_required

from app_kit.views import ManageGenericContent

from app_kit.view_mixins import MetaAppMixin

from .forms import GlossaryEntryForm, GlossaryEntryWithImageForm, GlossaryOptionsForm

from .models import Glossary, GlossaryEntry, TermSynonym

from localcosmos_server.generic_views import AjaxDeleteView

        
class ManageGlossary(ManageGenericContent):

    template_name = 'glossary/manage_glossary.html'
    options_form_class = GlossaryOptionsForm

    def get_glossary_entry_form(self):
        initial = {
            'glossary' : self.generic_content
        }
        return GlossaryEntryForm(initial=initial, language=self.generic_content.primary_language)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['glossary_entry_form'] = self.get_glossary_entry_form()
        context['glossary_entries'] = GlossaryEntry.objects.filter(glossary=self.generic_content)
        return context


class ManageGlossaryEntryCommon:

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.glossary = Glossary.objects.get(pk=kwargs['glossary_id'])
        self.set_glossary_entry(**kwargs)
        self.set_content_image()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):

        glossary_entry = form.save()

        context = self.get_context_data(**self.kwargs)
        context['saved_glossary_entry'] = True
        context['form'] = self.form_class(initial=self.get_initial(),
                                                         language=self.glossary.primary_language)
        context['glossary_entry'] = glossary_entry

        synonyms = form.cleaned_data.get('synonyms', [])

        if synonyms:

            synonyms_list = [s.strip() for s in synonyms.split(',')]

            existing_synonyms = [es.term for es in glossary_entry.synonyms]

            delete_synonyms = set(existing_synonyms) - set(synonyms_list)

            for delete_term in delete_synonyms:
                synonym = TermSynonym.objects.get(glossary_entry=glossary_entry, term=delete_term)
                synonym.delete()

            add_synonyms = set(synonyms_list) - set(existing_synonyms)
            for term in add_synonyms:

                if len(term) > 0:
                    synonym = TermSynonym(
                        glossary_entry=glossary_entry,
                        term=term,
                    )

                    synonym.save()

        # save the image, if any
        if 'source_image' in form.cleaned_data and form.cleaned_data['source_image']:
            self.content_instance = glossary_entry
            self.save_image(form)

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['generic_content'] = self.glossary
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['glossary'] = self.glossary
        return initial


from app_kit.views import ManageContentImageMixin
class AddGlossaryEntry(ManageContentImageMixin, ManageGlossaryEntryCommon, MetaAppMixin, FormView):

    template_name = 'glossary/ajax/add_glossary_entry.html'
    form_class = GlossaryEntryWithImageForm        
    
    def set_glossary_entry(self, **kwargs):
        self.glossary_entry = None

    def set_content_image(self):
        self.object_content_type = ContentType.objects.get_for_model(GlossaryEntry)
        self.content_image = None
        self.content_instance = self.glossary_entry
        self.new = True
        self.licence_registry_entry = None
        self.image_type = None
        self.taxon = None

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.glossary.primary_language
        return form_kwargs




class ManageGlossaryEntry(ManageGlossaryEntryCommon, MetaAppMixin, FormView):

    template_name = 'glossary/ajax/manage_glossary_entry.html'
    form_class = GlossaryEntryForm

    def set_glossary_entry(self, **kwargs):
        self.glossary_entry = GlossaryEntry.objects.get(pk=kwargs['glossary_entry_id'])

    def set_content_image(self):
        pass


    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['instance'] = self.glossary_entry
        form_kwargs['language'] = self.glossary_entry.glossary.primary_language
        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['glossary_entry'] = self.glossary_entry
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['glossary'] = self.glossary
        initial['synonyms'] = ','.join(self.glossary_entry.synonyms.values_list('term', flat=True))
        return initial
    


class GetGlossaryEntries(MetaAppMixin, TemplateView):

    template_name = 'glossary/ajax/glossary_entries.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.glossary = Glossary.objects.get(pk=kwargs['glossary_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['generic_content'] = self.glossary
        context['glossary_entries'] = GlossaryEntry.objects.filter(glossary=self.glossary)
        return context


class GetGlossaryEntry(MetaAppMixin, TemplateView):

    template_name = 'glossary/ajax/glossary_entry.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.glossary_entry = GlossaryEntry.objects.get(pk=kwargs['glossary_entry_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['glossary_entry'] = self.glossary_entry
        context['generic_content'] = self.glossary_entry.glossary
        return context


class DeleteGlossaryEntry(AjaxDeleteView):
    model = GlossaryEntry

    template_name = 'glossary/ajax/delete_glossary_entry.html'

    def form_valid(self, form):
        
        glossary_entry_id = self.object.id

        self.object.delete()

        context = {
            'glossary_entry_id' : glossary_entry_id,
            'deleted':True,
        }
        return self.render_to_response(context)

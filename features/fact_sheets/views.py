from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView
from django.utils.decorators import method_decorator

from django import forms

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin

from app_kit.models import MetaApp

from .forms import (CreateFactSheetForm, ManageFactSheetForm, UploadFactSheetImageForm,
                    UploadFactSheetTemplateForm)

from .models import (FactSheets, FactSheet, FactSheetImages, FactSheetTemplates,
                     build_factsheets_templates_upload_path)
                     
from .CMSTags import CMSTag

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator

from localcosmos_server.generic_views import AjaxDeleteView

import os


class ManageFactSheets(ManageGenericContent):
    template_name = 'fact_sheets/manage_fact_sheets.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        fact_sheets = FactSheet.objects.filter(fact_sheets=self.generic_content)
        context['fact_sheets'] = fact_sheets
        
        return context


class CreateFactSheet(MetaAppMixin, FormView):

    template_name = 'fact_sheets/create_fact_sheet.html'
    form_class = CreateFactSheetForm

    def dispatch(self, request, *args, **kwargs):
        self.generic_content = FactSheets.objects.get(pk=kwargs['fact_sheets_id'])
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['generic_content'] = self.generic_content
        
        return context


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.meta_app, self.generic_content, **self.get_form_kwargs())


    def get_initial(self):
        initial = super().get_initial()
        initial['input_language'] = self.generic_content.primary_language
        return initial


    def form_valid(self, form):

        fact_sheet = FactSheet(
            fact_sheets = self.generic_content,
            template_name = form.cleaned_data['template_name'],
            title = form.cleaned_data['title'],
            navigation_link_name = form.cleaned_data['navigation_link_name'],
            created_by = self.request.user,
        )

        fact_sheet.save()

        # save fact sheet and redirect
        return redirect('manage_factsheet', meta_app_id=self.meta_app.id, fact_sheet_id=fact_sheet.pk)
        
    

class ManageFactSheet(MetaAppMixin, FormView):

    template_name = 'fact_sheets/manage_atomic_fact_sheet.html'
    form_class = ManageFactSheetForm

    empty_values = ['', '<p>&nbsp;</p>', None]

    def dispatch(self, request, *args, **kwargs):
        self.fact_sheet = FactSheet.objects.get(pk=kwargs['fact_sheet_id'])
        return super().dispatch(request, *args, **kwargs)


    def get_initial(self):
        
        initial = {
            'title' : self.fact_sheet.title,
            'navigation_link_name' : self.fact_sheet.navigation_link_name,
            'input_language' : self.fact_sheet.fact_sheets.primary_language,
        }

        if self.fact_sheet.contents:
            for microcontent_type, data in self.fact_sheet.contents.items():
                initial[microcontent_type] = data
            
        return initial


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.meta_app, self.fact_sheet, **self.get_form_kwargs())


    def get_preview_url(self):
        app_preview_url_suffix = '/fact-sheet/{0}/?meta_app_id={1}'.format(self.fact_sheet.slug,
                                                                           self.meta_app.id)

        # the relative preview url
        unschemed_preview_url = '{0}#{1}'.format(self.meta_app.app.get_preview_url(), app_preview_url_suffix)

        # the host where the preview is served. on LCOS it is simply the website
        if unschemed_preview_url.startswith('http://') or unschemed_preview_url.startswith('https://'):
            preview_url = unschemed_preview_url
        else:
            preview_url = '{0}://{1}'.format(self.request.scheme, unschemed_preview_url)
        
        return preview_url
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fact_sheet'] = self.fact_sheet
        context['preview_url'] = self.get_preview_url()
        return context


    def form_valid(self, form):

        self.fact_sheet.title = form.cleaned_data['title']
        self.fact_sheet.navigation_link_name = form.cleaned_data['navigation_link_name']

        if not self.fact_sheet.contents:
            self.fact_sheet.contents = {}

        for field_ in form:

            field = field_.field
            if hasattr(field, 'cms_tag'):

                data = form.cleaned_data[field_.name]

                if data and type(data) in [str, list] and len(data) > 0 and data not in self.empty_values:

                    microcontent_type = field.cms_tag.microcontent_type

                    self.fact_sheet.contents[microcontent_type] = data

        self.fact_sheet.save()

        context = self.get_context_data(**self.kwargs)
        return self.render_to_response(context)


# primary language only
# CSRF exempt ?
# mapped in app_kit.urls to be accessible from the apps settings.API_URL
class GetFactSheetPreview(TemplateView):

    template_name = 'fact_sheets/fact_sheet_preview.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_factsheet(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_factsheet(self, **kwargs):
        slug = kwargs['slug']
        self.fact_sheet = FactSheet.objects.get(slug=slug)
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])


    def get_context_data(self, **kwargs):
        
        context = {
            'html' : self.fact_sheet.render_as_html(self.meta_app),
        }

        return context


'''
    There are 2 types of images:
    - images/files that are microcontent_types themselves
    - images/files that are added to a text microcontent_type via ckeditor
'''
from content_licencing.view_mixins import LicencingFormViewMixin
class UploadFactSheetImage(LicencingFormViewMixin, FormView):

    template_name = 'fact_sheets/factsheet_image_form.html'

    form_class = UploadFactSheetImageForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_file(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_file(self, **kwargs):
        self.fact_sheet = FactSheet.objects.get(pk=kwargs['fact_sheet_id'])
        self.microcontent_category = kwargs['microcontent_category']
        self.microcontent_type = kwargs['microcontent_type']

        self.image = None

        if 'pk' in kwargs:
            self.image = FactSheetImages.objects.get(pk=kwargs['pk'])

            self.set_licence_registry_entry(self.image, 'image')
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fact_sheet'] = self.fact_sheet
        context['microcontent_category'] = self.microcontent_category
        context['microcontent_type'] = self.microcontent_type
        context['success'] = False
        context['image'] = self.image
        return context



    def get_initial(self):
        initial = super().get_initial()

        if self.image:
            initial['source_image'] = self.image.image
            licencing_initial = self.get_licencing_initial()
            initial.update(licencing_initial)

        return initial
            

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        if self.image:
            form_kwargs['current_image'] = self.image
        return form_kwargs


    def form_valid(self, form):

        image_file = form.cleaned_data['source_image']

        if not self.image:
            self.image = FactSheetImages(
                fact_sheet = self.fact_sheet,
                microcontent_type = self.microcontent_type,
            )

        self.image.image = image_file

        self.image.save()

        self.register_content_licence(form, self.image, 'image')
        self.set_licence_registry_entry(self.image, 'image')

        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        context['image'] = self.image

        return self.render_to_response(context)



class DeleteFactSheetImage(AjaxDeleteView):
    
    model = FactSheetImages

    template_name = 'fact_sheets/ajax/delete_fact_sheet_image.html'

    def get_verbose_name(self):
        name = ' '.join(self.object.microcontent_type.split('_')).capitalize()
        return name

    def get_context_data(self, **kwargs):
        microcontent_category = self.request.GET['microcontent_category']
        context = super().get_context_data(**kwargs)
        context['fact_sheet'] = self.object.fact_sheet
        context['microcontent_type'] = self.object.microcontent_type
        context['microcontent_category'] = microcontent_category
        context['url'] = '{0}?microcontent_category={1}'.format(self.request.path, microcontent_category)
        return context
    
'''
    get all fields for a microcontent_type
    ajax only
    for successful image deletions and uploads
    reloads all fields if field is multi
'''
class GetFactSheetFormField(FormView):

    template_name = 'fact_sheets/ajax/reloaded_file_fields.html'
    form_class = forms.Form

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_content(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_content(self, **kwargs):
        self.fact_sheet = FactSheet.objects.get(pk=kwargs['fact_sheet_id'])
        self.microcontent_category = kwargs['microcontent_category']
        self.microcontent_type = kwargs['microcontent_type']
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fact_sheet'] = self.fact_sheet
        return context
    

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = forms.Form

        cms_tag = CMSTag(self.fact_sheet, self.microcontent_category, self.microcontent_type)

        form = form_class(**self.get_form_kwargs())

        instances = FactSheetImages.objects.filter(fact_sheet=self.fact_sheet,
                                                   microcontent_type=self.microcontent_type)

        for field in cms_tag.form_fields(instances=instances):
            form.fields[field['name']] = field['field']

        return form


class UploadFactSheetTemplate(MetaAppMixin, FormView):

    template_name = 'fact_sheets/ajax/upload_factsheet_template.html'
    form_class = UploadFactSheetTemplateForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.fact_sheets = FactSheets.objects.get(pk=kwargs['fact_sheets_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.fact_sheets, **self.get_form_kwargs())


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fact_sheets'] = self.fact_sheets
        context['success'] = False
        return context
        

    def form_valid(self, form):

        template_file = form.cleaned_data['template']

        path = build_factsheets_templates_upload_path(self.fact_sheets, template_file.name)

        template = FactSheetTemplates.objects.filter(fact_sheets = self.fact_sheets, template = path).first()

        if template:
            if template.template and os.path.isfile(template.template.path):
                os.remove(template.template.path)
        else:
            template = FactSheetTemplates(
                fact_sheets = self.fact_sheets,
            )

        template.template = template_file
        template.uploaded_by = self.request.user
        template.name = form.cleaned_data.get('name', None)
        template.save()

        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True

        return self.render_to_response(context)

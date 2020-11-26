from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView
from django.utils.decorators import method_decorator

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin

from .forms import CreateFactSheetForm, ManageFactSheetForm
from .models import FactSheets, FactSheet

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
        return form_class(self.meta_app, **self.get_form_kwargs())


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
        return redirect('manage_factsheet', meta_app_id=self.meta_app.id, pk=fact_sheet.pk)
        
    

class ManageFactSheet(MetaAppMixin, FormView):

    template_name = 'fact_sheets/manage_atomic_fact_sheet.html'
    form_class = ManageFactSheetForm

    empty_values = ['', '<p>&nbsp;</p>', None]

    def dispatch(self, request, *args, **kwargs):
        self.fact_sheet = FactSheet.objects.get(pk=kwargs['fact_sheet_id'])
        return super().dispatch(request, *args, **kwargs)


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.meta_app, self.fact_sheet, **self.get_form_kwargs())


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fact_sheet'] = self.fact_sheet
        return context


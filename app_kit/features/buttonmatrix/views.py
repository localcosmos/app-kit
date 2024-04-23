from django.views.generic import TemplateView, FormView

from django.contrib.contenttypes.models import ContentType

from .models import (ButtonMatrix, ButtonMatrixButton, ButtonExtension)

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator

from django.utils.translation import gettext as _

from app_kit.models import MetaApp

from .forms import MatrixButtonForm, ButtonMatrixOptionsForm
from app_kit.features.generic_forms.models import (GenericForm, DJANGO_FIELD_CLASSES, GenericField,
      GenericFieldToGenericForm)

import json

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppFormLanguageMixin

form_builder_path = 'app_kit.appbuilder.JSONBuilders.GenericForm.1.GenericFormJSONBuilder.GenericFormJSONBuilder'
from app_kit.utils import import_class
GenericFormJSONBuilder = import_class(form_builder_path)


class ManageButtonMatrix(ManageGenericContent):

    template_name = 'buttonmatrix/manage_buttonmatrix.html'
    options_form_class = ButtonMatrixOptionsForm

    def get_initial(self):
        initial = super().get_initial()
        initial['rows'] = self.generic_content.rows
        initial['columns'] = self.generic_content.columns
        
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        generic_form = self.generic_content.get_option(self.meta_app, 'generic_form')
        exposed_field_option = self.generic_content.get_option(self.meta_app, 'generic_form_exposed_field')
        if exposed_field_option:
            # the field might have been deleted
            field_link = GenericFieldToGenericForm.objects.filter(
                generic_form__uuid = generic_form['uuid'],
                generic_field__uuid = exposed_field_option['uuid'],
            ).first()

            if field_link:
                
                context['exposed_field_link'] = field_link

                # use the JSONBuilder - v1
                formbuilder = GenericFormJSONBuilder()
                field_json = formbuilder._create_generic_form_field_dic(field_link,
                                                                        language_code=self.primary_language)
                context['exposed_field_json'] = json.dumps(field_json)
        return context

    def post(self, request, *args, **kwargs):
        
        form = self.options_form_class(request.POST, meta_app=self.meta_app,
                                       generic_content=self.generic_content)

        if form.is_valid():

            if form.cleaned_data['rows'] and form.cleaned_data['columns']:

                self.generic_content.rows = form.cleaned_data['rows']
                self.generic_content.columns = form.cleaned_data['columns']
                self.generic_content.save()

        return super().post(request, *args, **kwargs)


from django.db.models.fields import BLANK_CHOICE_DASH
class GetButtonMatrixExposedFieldOptions(FormView):

    template_name = 'buttonmatrix/ajax/generic_form_exposed_field_options.html'
    form_class = ButtonMatrixOptionsForm

    def get(self, request, *args, **kwargs):
        self.generic_content = ButtonMatrix.objects.get(pk=self.kwargs['buttonmatrix_id'])
        self.meta_app = MetaApp.objects.get(pk=self.kwargs['meta_app_id'])
        self.generic_form = None
        if 'generic_form_uuid' in kwargs:
            self.generic_form = GenericForm.objects.get(uuid=self.kwargs['generic_form_uuid'])
        
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        self.generic_content.global_options = {}
        form_kwargs = {
            'meta_app' : self.meta_app,
            'generic_content' : self.generic_content,
            'initial' : self.get_initial(),
            'exposed_field_form' : self.generic_form,
        }
        
        return form_kwargs


class ManageButtonMatrixButton(MetaAppFormLanguageMixin, FormView):

    template_name = 'buttonmatrix/manage_button.html'
    form_class = MatrixButtonForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):

        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        
        self.button_matrix = ButtonMatrix.objects.get(pk=self.kwargs['button_matrix_id'])

        self.generic_form = None
        generic_form_option = self.button_matrix.get_option(self.meta_app, 'generic_form')
        if generic_form_option:
            self.generic_form = GenericForm.objects.get(uuid=generic_form_option['uuid'])
        
        self.row = int(self.kwargs['row'])
        self.column = int(self.kwargs['column'])
        self.button = ButtonMatrixButton.objects.filter(button_matrix=self.button_matrix, row=self.row,
                                                        column=self.column).first()
        
        if self.button:
            self.button.load_taxon()

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs.update({
            'language' : self.primary_language,
            'generic_form' : self.generic_form,
        })
        if self.button:
            kwargs['instance'] = self.button
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.button:
            initial['taxon'] = self.button.taxon
        else:
            initial.update({
                'button_matrix' : self.button_matrix.id,
                'row' : self.row,
                'column' : self.column,
            })

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['button_matrix'] = self.button_matrix
        context['row'] = self.row
        context['column'] = self.column
        
        if self.button:
            context['button'] = self.button
            context['buttonextensions'] = ButtonExtension.objects.filter(
                button=self.button).distinct('generic_field')
        else:
            context['buttonextensions'] = []
                
        return context

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)
        
        instance = form.save()
        instance.load_taxon()
        context['button'] = instance

        context['form'] = form

        return self.render_to_response(context)


class DeleteButtonMatrixElement(TemplateView):

    template_name = "buttonmatrix/delete_buttonmatrix_element.html"

    def dispatch(self, request, *args, **kwargs):

        self.object_content_type = kwargs["content_type"]

        self.object = None
        self.object_pk = None

        if self.object_content_type == "button":
            self.object = ButtonMatrixButton.objects.filter(pk=kwargs["object_pk"]).first()
        elif self.object_content_type == "extension":
            self.object = ButtonExtension.objects.filter(pk=kwargs["object_pk"]).first()
        else:
            raise ValueError("content type %s is not known to the button matrix feature" % kwargs["content_type"])

        if self.object:
            self.object_pk = self.object.pk

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            "object_pk" : self.object_pk,
            "content_type" : self.object_content_type,
        }
        return context


    @method_decorator(ajax_required)
    def post(self, request, *args, **kwargs):

        context = self.get_context_data(**kwargs)

        if self.object:
            self.object.delete()

        context["deleted"] = True

        return self.render_to_response(context)

    @method_decorator(ajax_required)
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context["deleted"] = False
        
        return self.render_to_response(context)

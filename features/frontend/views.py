from django.utils.decorators import method_decorator
from django.views.generic import FormView

from django.contrib.contenttypes.models import ContentType

from localcosmos_server.decorators import ajax_required

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin

from app_kit.appbuilder import AppBuilder

from .forms import FrontendSettingsForm

from .models import Frontend, FrontendText


class FrontendSettingsMixin:

    def get_form(self):
        form = self.form_class(*self.get_form_args(), **self.get_form_kwargs())
        return form

    def get_form_args(self):
        form_args = [self.meta_app, self.generic_content]
        return form_args


    def get_frontend_settings(self):

        app_builder = AppBuilder(self.meta_app)
        frontend_settings = app_builder._get_frontend_settings()
        return frontend_settings


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['frontend'] = self.generic_content
        frontend_settings = self.get_frontend_settings()
        context['frontend_settings'] = frontend_settings

        context['success'] = False

        return context


    def get_text_types(self):
        frontend_settings = self.get_frontend_settings()
        text_types = list(frontend_settings['userContent']['texts'].keys())
        text_types.append('legal_notice')

        return text_types


    def get_initial(self):

        initial = {}

        text_types = self.get_text_types()

        for text_type in text_types:

            frontend_text = FrontendText.objects.filter(frontend=self.generic_content,
                                identifier=text_type).first()

            if frontend_text:
                initial[text_type] = frontend_text.text

        
        return initial



'''
    - read frontend settings, which contains required images and texts
'''
class ManageFrontend(FrontendSettingsMixin, ManageGenericContent):

    template_name = 'frontend/manage_frontend.html'
    form_class = FrontendSettingsForm

    def get_form(self):
        form = self.form_class(*self.get_form_args(), initial=self.get_initial())
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['frontend_settings_form'] = self.get_form()
        return context


# ajax save settings
class ManageFrontendSettings(FrontendSettingsMixin, MetaAppMixin, FormView):
    
    form_class = FrontendSettingsForm
    template_name = 'frontend/ajax/manage_frontend_settings.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_frontend(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_frontend(self, **kwargs):
        self.generic_content = Frontend.objects.get(pk=kwargs['frontend_id'])
        self.frontend = self.generic_content
        self.content_type = ContentType.objects.get_for_model(Frontend)


    def form_valid(self, form):

        text_types = self.get_text_types()

        for text_type in text_types:
            
            if text_type in form.cleaned_data:

                text = form.cleaned_data[text_type]

                frontend_text = FrontendText.objects.filter(frontend=self.frontend, identifier=text_type).first()

                if not frontend_text:
                    frontend_text = FrontendText(
                        frontend=self.frontend,
                        frontend_name=self.frontend.frontend_name,
                        identifier=text_type,
                    )

                frontend_text.text = text

                frontend_text.save()

        
        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)

        
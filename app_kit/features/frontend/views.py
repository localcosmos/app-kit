from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView
from django.db import connection
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.decorators import ajax_required

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin

from app_kit.appbuilder import AppBuilder, AppPreviewBuilder

from .forms import FrontendSettingsForm, ChangeFrontendForm, UploadPrivateFrontendForm, InstallPrivateFrontendForm

from .models import Frontend, FrontendText

from .PrivateFrontendImporter import PrivateFrontendImporter

import threading


class FrontendSettingsMixin:

    def get_form(self):
        form = self.form_class(*self.get_form_args(), **self.get_form_kwargs())
        return form

    def get_form_args(self):
        form_args = [self.meta_app, self.generic_content]
        return form_args


    def get_preview_build_frontend_settings(self):
        preview_builder = AppPreviewBuilder(self.meta_app)
        app_settings = preview_builder.get_app_settings()
        return app_settings
    

    def get_frontend_settings(self):
        app_builder = AppBuilder(self.meta_app)
        frontend_settings = app_builder._get_frontend_settings()
        return frontend_settings
    
    
    def compare_versions(self, version1, version2):
    # Split the version strings into lists of integers
        v1_parts = list(map(int, version1.split('.')))
        v2_parts = list(map(int, version2.split('.')))

        # Determine the maximum length to compare all parts
        max_length = max(len(v1_parts), len(v2_parts))

        # Compare each part
        for i in range(max_length):
            # If one version string is shorter, treat missing parts as zero
            v1_part = v1_parts[i] if i < len(v1_parts) else 0
            v2_part = v2_parts[i] if i < len(v2_parts) else 0

            if v1_part < v2_part:
                return -1
            elif v1_part > v2_part:
                return 1

        # If we've made it here, the versions are equal
        return 0


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['new_frontend_version_available'] = False
        context['frontend'] = self.generic_content
        frontend_settings = self.get_frontend_settings()
        context['frontend_settings'] = frontend_settings
        preview_build_settings = self.get_preview_build_frontend_settings()
        context['preview_build_settings'] = preview_build_settings

        frontend_version = frontend_settings['version']
        preview_build_version = preview_build_settings['version']
        new_frontend_version_available = self.compare_versions(frontend_version, preview_build_version)

        if new_frontend_version_available == 1:
            context['new_frontend_version_available'] = True

        context['success'] = False

        return context


    def get_text_types(self):
        frontend_settings = self.get_frontend_settings()
        text_types = list(frontend_settings['userContent']['texts'].keys())
        text_types.append('legal_notice')
        text_types.append('privacy_policy')

        return text_types

    def get_configuration_keys(self):

        configuration_keys = ['support_email']
        frontend_settings = self.get_frontend_settings()

        if 'configuration' in frontend_settings['userContent']:
            configuration_keys = configuration_keys + list(frontend_settings['userContent']['configuration'].keys())
        
        return configuration_keys


    def get_initial(self):

        initial = {}

        text_types = self.get_text_types()

        for text_type in text_types:

            frontend_text = FrontendText.objects.filter(frontend=self.generic_content,
                        identifier=text_type, frontend_name=self.generic_content.frontend_name).first()

            if frontend_text:
                initial[text_type] = frontend_text.text

        if self.generic_content.configuration:

            for configuration_key, configuration_value in self.generic_content.configuration.items():
                initial[configuration_key] = configuration_value
        
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

                frontend_text = FrontendText.objects.filter(frontend=self.frontend,
                    frontend_name=self.frontend.frontend_name, identifier=text_type).first()

                if not frontend_text:
                    frontend_text = FrontendText(
                        frontend=self.frontend,
                        frontend_name=self.frontend.frontend_name,
                        identifier=text_type,
                    )

                frontend_text.text = text

                frontend_text.save()

        self.frontend.configuration = {}
        configuration_keys = self.get_configuration_keys()
        for configuration_key in configuration_keys:
            configuration_value = form.cleaned_data.get(configuration_key, None)
            if configuration_value:
                self.frontend.configuration[configuration_key] = configuration_value
        
        self.frontend.save()
        
        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)


class FrontendMixin:

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_frontend(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['frontend'] = self.frontend
        return context

    def set_frontend(self, **kwargs):
        self.frontend = Frontend.objects.get(pk=kwargs['frontend_id'])
        self.generic_content = self.frontend

    # runs async in thread
    def update_frontend(self, frontend_name):

        self.frontend.frontend_name = frontend_name
        self.frontend.save()

        def run_in_thread():

            # threading resets the connection -> set to tenant
            connection.set_tenant(self.request.tenant)

            self.frontend.lock('preview_build')

            try:
                preview_builder = self.meta_app.get_preview_builder()
                preview_builder.build()
                self.frontend.unlock()

            except Exception as e:

                self.frontend.messages['last_preview_build_errors'] = [str(e)]

                # unlock generic content
                self.frontend.unlock()

        thread = threading.Thread(target=run_in_thread)
        thread.start()


class ChangeFrontend(FrontendMixin, MetaAppMixin, FormView):

    template_name = 'frontend/ajax/change_frontend.html'
    form_class = ChangeFrontendForm

    def get_initial(self):
        initial = super().get_initial()
        initial['frontend_name'] = self.frontend.frontend_name
        return initial


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.meta_app, **self.get_form_kwargs())


    def form_valid(self, form):

        frontend_name = form.cleaned_data['frontend_name']
        self.update_frontend(frontend_name)

        context = self.get_context_data(**self.kwargs)
        context['success'] = True

        return self.render_to_response(context)


'''
    disallow private frontends that have the same name as public frontends
'''
class UploadPrivateFrontend(FrontendMixin, MetaAppMixin, FormView):

    template_name = 'frontend/ajax/upload_private_frontend.html'
    form_class = UploadPrivateFrontendForm

    def form_valid(self, form):

        context = self.get_context_data(**self.kwargs)

        uploaded_zip = form.cleaned_data['frontend_zip']

        zip_importer = PrivateFrontendImporter(self.meta_app)
        zip_importer.unzip_to_temporary_folder(uploaded_zip)
        is_valid = zip_importer.validate()

        context['errors'] = zip_importer.errors
        context['success'] = False
        context['frontend_settings'] = {}

        if is_valid == True:
            frontend_settings = zip_importer.get_frontend_settings()
            context['success'] = True
            context['frontend_settings'] = frontend_settings
            context['form'] = InstallPrivateFrontendForm(initial={'frontend_name':frontend_settings['frontend']})
            
        return self.render_to_response(context)
            


class InstallPrivateFrontend(FrontendMixin, MetaAppMixin, FormView):

    template_name = 'frontend/ajax/install_private_frontend.html'
    form_class = InstallPrivateFrontendForm

    def form_valid(self, form):

        context = self.get_context_data(**self.kwargs)

        frontend_name = form.cleaned_data['frontend_name']

        zip_importer = PrivateFrontendImporter(self.meta_app)
        zip_importer.validate()

        context['success'] = False

        if zip_importer.is_valid and frontend_name == zip_importer.get_frontend_name():

            zip_importer.install_frontend()
            self.update_frontend(frontend_name)

            context['success'] = True


        return self.render_to_response(context)


class UpdateUsedFrontend(FrontendSettingsMixin, FrontendMixin, MetaAppMixin, TemplateView):
    
    template_name = 'frontend/ajax/update_used_frontend.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['updating'] = False
        return context
    
    def post(self, request, *args, **kwargs):

        context = self.get_context_data(**self.kwargs)
        
        frontend_name = context['frontend_settings']['frontend']
        
        self.update_frontend(frontend_name)

        context['updating'] = True
            
        return self.render_to_response(context)
    
    
from django.conf import settings
from django.shortcuts import redirect
from django.views.generic import TemplateView, FormView
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt, requires_csrf_token

# do not use connection.close in threads
from django.db import close_old_connections

from django.core import mail

from .models import (MetaApp, MetaAppGenericContent, ImageStore, ContentImage, LocalizedContentImage,
                     AppKitSeoParameters)

from .generic import AppContentTaxonomicRestriction

from .forms import (AddLanguageForm, MetaAppOptionsForm, TagAnyElementForm, GenericContentStatusForm,
                    CreateGenericContentForm, AddExistingGenericContentForm, TranslateAppForm,
                    EditGenericContentNameForm, ManageContentImageWithTextForm,
                    ZipImportForm, BuildAppForm, CreateAppForm, ManageLocalizedContentImageForm,
                    TranslateVernacularNamesForm)

from django_tenants.utils import get_tenant_domain_model
Domain = get_tenant_domain_model()

from app_kit.app_kit_api.models import AppKitJobs, AppKitStatus

from app_kit.appbuilder import AppBuilder, AppPreviewBuilder
from app_kit.appbuilder.ContentImageBuilder import ContentImageBuilder

from .view_mixins import ViewClassMixin, MetaAppMixin, MetaAppFormLanguageMixin

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator


from taxonomy.lazy import LazyTaxon, LazyTaxonList
from taxonomy.models import TaxonomyModelRouter, MetaVernacularNames

from content_licencing.view_mixins import LicencingFormViewMixin

from localcosmos_server.generic_views import AjaxDeleteView, ManageSeoParameters

import deepl

import json, urllib.request, urllib.parse, urllib.error, traceback, threading
from django.db import connection

# activate permission rules
from .permission_rules import *

LOCALCOSMOS_COMMERCIAL_BUILDER = getattr(settings, 'LOCALCOSMOS_COMMERCIAL_BUILDER', True)


'''
    The default PasswordResetView sends an email without subdomain in the link
    - provide email_extra_context with request.get_host() which returns the domain with subdomain
'''
from django.contrib.auth.views import PasswordResetView
class TenantPasswordResetView(PasswordResetView):
    
    email_template_name = 'localcosmos_server/registration/password_reset_email.html'

    def dispatch(self, request, *args, **kwargs):
        self.extra_email_context = {
            'tenant_domain' : request.get_host(),
        }
        return super().dispatch(request, *args, **kwargs)


'''
    Generic content creation via form
    All generic content only needs a name for creation
    gets the model class, uses the create function with name as param
    creates a link from the content to the app
'''

'''
    CreateGenericContent - abstract view
    its Subclass CreateGenericAppContent creates app feature contents like Form etc
'''
class CreateGenericContent(FormView):

    template_name = 'app_kit/ajax/create_generic_content.html'

    form_class = CreateGenericContentForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_primary_language(request, **kwargs)
        self.set_content_type_id(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_primary_language(self, request, **kwargs):
        raise NotImplementedError('CreateGenericContent Subclasses need a set_primary_language method')

    def set_content_type_id(self, **kwargs):
        raise NotImplementedError('CreateGenericContent Subclasses need a set_content_type_id method')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type_id'] = self.generic_content_type_id
        context['content_type'] = ContentType.objects.get(pk=self.generic_content_type_id)
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['content_type_id'] = self.generic_content_type_id
        return initial

    def get_create_kwargs(self, request):
        return {}

    def save(self, form):
        context = self.get_context_data(**self.kwargs)
        
        self.generic_content_type = ContentType.objects.get(pk=form.cleaned_data['content_type_id'])

        ContentModel = self.generic_content_type.model_class()

        self.created_content = ContentModel.objects.create(form.cleaned_data['name'], self.primary_language,
                                                           **self.get_create_kwargs(self.request))

        context['created_content'] = self.created_content

        return context
        

    def form_valid(self, form):
        context = self.save(form)
        return self.render_to_response(context)


'''
    the primary language is read from the form for the App creation
'''
class CreateApp(CreateGenericContent):

    form_class = CreateAppForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_content_type_id(**kwargs)
        
        # check if app creation is allowed
        app_count = MetaApp.objects.all().count()

        if request.tenant.number_of_apps and app_count >= request.tenant.number_of_apps:
            return redirect(reverse('app_limit_reached'))
        
        return super(CreateGenericContent, self).dispatch(request, *args, **kwargs)


    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        if self.request.user.is_superuser:
            form_kwargs['allow_uuid'] = True
        return form_kwargs


    def get_initial(self, **kwargs):
        initial = super().get_initial(**kwargs)
        initial['primary_language'] = self.request.LANGUAGE_CODE[:2]
        return initial

    def set_primary_language(self, request, **kwargs):
        self.primary_language = self.form.cleaned_data['primary_language']

    def set_content_type_id(self, **kwargs):
        meta_app_type = ContentType.objects.get_for_model(MetaApp)
        self.generic_content_type_id = meta_app_type.id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_app_creation'] = True
        return context

    # app needs to be set
    def save(self, form):
        self.form = form
        self.set_primary_language(self.request)
        
        public_domain = Domain.objects.get(tenant__schema_name='public', is_primary=True)

        # the url of the app
        app_domain_name = '{}.{}'.format(form.cleaned_data['subdomain'], public_domain.domain)

        meta_app_kwargs = {}

        if 'uuid' in form.cleaned_data and form.cleaned_data['uuid']:
            meta_app_kwargs['uuid'] = form.cleaned_data['uuid']

        if 'frontend' in form.cleaned_data and form.cleaned_data['frontend']:
            meta_app_kwargs['frontend'] = form.cleaned_data['frontend']
            
        meta_app = MetaApp.objects.create(form.cleaned_data['name'],
                                    form.cleaned_data['primary_language'], app_domain_name, self.request.tenant,
                                    form.cleaned_data['subdomain'], **meta_app_kwargs)

        self.created_content = meta_app

        # MetaApp and all required features have been created

        def run_in_thread():
            # threading resets the connection -> set to tenant
            connection.set_tenant(self.request.tenant)

            # create the version specific folder on disk
            # fails if the version already exists
            app_builder = AppBuilder(meta_app)
            app_builder.create_app_version()

            # create preview
            app_preview_builder = AppPreviewBuilder(meta_app)
            app_preview_builder.build()

            close_old_connections()

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        
        context = self.get_context_data(**self.kwargs)
        context['meta_app'] = self.created_content
        context['created_content'] = self.created_content
        return context
    

class GetAppCard(MetaAppMixin, TemplateView):

    template_name = 'app_kit/ajax/app_card.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = ContentType.objects.get_for_model(self.meta_app)
        return context

    
class AppLimitReached(TemplateView):

    template_name = 'app_kit/ajax/app_limit_reached.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):        
        return super().dispatch(request, *args, **kwargs)
        

class DeleteApp(AjaxDeleteView):

    model = MetaApp

    def get_deletion_message(self):
        return _('Do you really want to delete %s?' % self.object)

    def form_valid(self, form):

        domain = Domain.objects.get(app=self.object.app)
        # this will NOT delete the Domain entry
        if domain.is_primary == False:
            domain.delete()

        self.object.app.delete()
    
        context = self.get_context_data(**self.kwargs)
        context['deleted_object_id'] = self.object.pk
        context['deleted'] = True
        self.object.delete()
        return self.render_to_response(context)


class CreateGenericAppContent(CreateGenericContent):

    def dispatch(self, request, *args, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        return super().dispatch(request, *args, **kwargs)

    def set_content_type_id(self, **kwargs):
        self.generic_content_type_id = kwargs['content_type_id']
        self.generic_content_type = ContentType.objects.get(pk=kwargs['content_type_id'])

    def set_primary_language(self, request, **kwargs):
        self.primary_language = self.meta_app.primary_language


    def get_initial(self):
        initial = super().get_initial()
        initial['input_language'] = self.primary_language
        return initial

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.primary_language
        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_app'] = self.meta_app
        # check if it is a single content
        appbuilder = self.meta_app.get_preview_builder()
        ContentModel = self.generic_content_type.model_class()

        disallow_single_content = False
        if ContentModel.feature_type() in appbuilder.single_content_features and MetaAppGenericContent.objects.filter(meta_app=self.meta_app, content_type=self.generic_content_type).exists():
            disallow_single_content = True

        context['disallow_single_content'] = disallow_single_content

        return context

    # app to feature has to be saved
    def save(self, form):
        context = super().save(form)
        
        applink = MetaAppGenericContent (
            meta_app = self.meta_app,
            content_type_id = self.generic_content_type_id,
            object_id = self.created_content.id,
        )

        applink.save()

        context['meta_app'] = self.meta_app
        context['link'] = applink
        return context
        

class GetGenericContentCard(MetaAppFormLanguageMixin, TemplateView):

    template_name = 'app_kit/ajax/component_card.html'

    def dispatch(self, request, *args, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        self.link = MetaAppGenericContent.objects.get(pk=kwargs['generic_content_link_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['link'] = self.link
        return context

'''
    Managing GenericContent and its Subclasses
    these classes all need self.meta_app
'''
class ManageGenericContent(ViewClassMixin, MetaAppFormLanguageMixin, TemplateView):

    options_form_class = None

    def dispatch(self, request, *args, **kwargs):
        self.set_content(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_content(self, **kwargs):
        self.generic_content_type = ContentType.objects.get(pk=self.kwargs['content_type_id'])        
        self.generic_content = self.generic_content_type.get_object_for_this_type(pk=self.kwargs['object_id'])

    def set_languages(self):
        self.languages = self.meta_app.languages()
        self.primary_language = self.meta_app.primary_language
        
    def get_context_data(self, **kwargs):
        self.set_languages()

        self.generic_content.refresh_from_db()
        self.meta_app.refresh_from_db()
        
        context = {
            'generic_content' : self.generic_content,
            'content_type' : self.generic_content_type,
            'languages' : self.languages,
            'primary_language' : self.primary_language,
            'meta_app' : self.meta_app,
        }

        if self.options_form_class is not None:
            context['options_form'] = self.options_form_class(**self.get_options_form_kwargs())

        return context

    def get_options_form_kwargs(self):

        form_kwargs = {
            'meta_app' : self.meta_app,
            'generic_content' : self.generic_content,
            'initial' : self.get_initial(),
        }

        return form_kwargs
        

    # initial for GenericContentOptionsForm subclass
    def get_initial(self):
        return {}


    def post(self, request, *args, **kwargs):

        saved_options = False

        # save options
        if self.options_form_class is not None:
            options_form = self.options_form_class(request.POST, **self.get_options_form_kwargs())

            if options_form.is_valid():

                # get global_options
                if self.generic_content.global_options:
                    global_options = self.generic_content.global_options
                else:
                    global_options = {}

                # get app dependant options
                app_generic_content = self.meta_app.get_generic_content_link(self.generic_content)
                options = {}
                if app_generic_content:
                    options = app_generic_content.options
                    
                if not options:
                    options = {}

                altered_global_options = False
                altered_options = False

                # iterate over the submitted data
                for key, value in options_form.cleaned_data.items():

                    # decide if the value resides in options or global options
                    # this does not copy the dict, but point to it
                    options_ = options
                    if key in options_form.global_options_fields:
                        options_ = global_options
                        altered_global_options = True
                    else:
                        altered_options = True

                    # store or remove the key/value pair from json
                    if value:
                        # if the key is in the forms instance fields, save it as an instance
                        if key in options_form.instance_fields:
                            option_instance = options_form.uuid_to_instance[value]
                            option = self.generic_content.make_option_from_instance(option_instance)
                            options_[key] = option
                        else:
                            options_[key] = value
                    else:
                        
                        if key in options_:
                            del options_[key]

                # save altered options on app and link
                if altered_global_options == True:
                    self.generic_content.global_options = global_options
                    self.generic_content.save(increment_version=False)

                if altered_options == True:
                    app_generic_content.options = options
                    app_generic_content.save()

                saved_options = True

        else:
            options_form = None

        context = self.get_context_data(**kwargs)

        context['options_form'] = options_form
        context['posted'] = True
        context['saved_options'] = saved_options

        return self.render_to_response(context)

    def verbose_view_name(self, **kwargs):
        self.kwargs = kwargs
        self.set_content(**kwargs)
        return str(self.generic_content)



'''
    ManageApp
    - only for the commercial installation
'''

class ManageApp(ManageGenericContent):

    template_name = 'app_kit/manage_app.html'

    options_form_class = MetaAppOptionsForm    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appbuilder = self.meta_app.get_preview_builder()
        context['appbuilder'] = appbuilder
        context['form'] = AddLanguageForm()
        context['generic_content_links'] = MetaAppGenericContent.objects.filter(meta_app=self.generic_content)
        context['app_generic_content_type'] = ContentType.objects.get_for_model(MetaAppGenericContent)
        return context



class EditGenericContentName(FormView):

    form_class = EditGenericContentNameForm
    template_name = 'app_kit/ajax/edit_generic_content_name.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):        
        self.set_content(**kwargs)

        return super().dispatch(request, *args, **kwargs)


    def set_content(self, **kwargs):
        self.generic_content_type = ContentType.objects.get(pk=self.kwargs['content_type_id'])        
        self.generic_content = self.generic_content_type.get_object_for_this_type(
            pk=self.kwargs['generic_content_id'])
        
        self.primary_language = self.generic_content.primary_language

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_meta_app = False
        if self.generic_content_type == ContentType.objects.get_for_model(MetaApp):
            is_meta_app = True
        context['content_type'] = self.generic_content_type
        context['generic_content'] = self.generic_content
        context['is_meta_app'] = is_meta_app
        return context

    def get_initial(self):
        initial = super().get_initial()

        initial.update({
            'content_type_id' : self.generic_content_type.id,
            'generic_content_id' : self.generic_content.id,
            'name' : self.generic_content.name,
            'description': self.generic_content.get_global_option('description')
        })

        return initial

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.primary_language
        return form_kwargs

    def form_valid(self, form):

        content_type = ContentType.objects.get(pk=form.cleaned_data['content_type_id'])
        generic_content = content_type.get_object_for_this_type(pk=form.cleaned_data['generic_content_id'])

        description = form.cleaned_data['description']

        if description:
            if not generic_content.global_options:
                generic_content.global_options = {}
            
            generic_content.global_options['description'] = description

        # meta_app has the name stored on meta_app.app

        if content_type == ContentType.objects.get_for_model(MetaApp):
            generic_content.app.name = form.cleaned_data['name']
            generic_content.app.save()
        else:
            generic_content.name = form.cleaned_data['name']
            generic_content.save()
        
        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        # supply the context with the updated generic_content
        context['generic_content'] = generic_content
        return self.render_to_response(context)
        


'''
    TRANSLATING AN APP
'''
class PagedTranslationFormMixin:
    
    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        page = self.request.GET.get('page', 1)
        form_kwargs['page'] = int(page)
        return form_kwargs
    
    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.meta_app, **self.get_form_kwargs())


class TranslateApp(PagedTranslationFormMixin, MetaAppMixin, FormView):

    form_class = TranslateAppForm
    template_name = 'app_kit/translate_app.html'

    
    def dispatch(self, request, *args, **kwargs):
        self.fill_primary_localization(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def fill_primary_localization(self, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        # fill meta_app.localizations.json
        app_builder = self.meta_app.get_app_builder()
        app_builder.fill_primary_localization()

    '''
    update the translation files
    - use form.translations instead of cleaned_data, the latter is b64encoded
    '''
    def form_valid(self, form):
        
        for language_code, translation_dict in form.translations.items():

            if language_code not in self.meta_app.localizations:
                self.meta_app.localizations[language_code] = {}

            # value can be a file/image
            for key, value in translation_dict.items():

                # images are saved separately (TwoStepFileInput)
                if key.startswith('localized_content_image') == True:
                    continue

                else:
                    self.meta_app.localizations[language_code][key] = value
            

        self.meta_app.save()
            
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['saved'] = True
        return self.render_to_response(context)



'''
    Fetch automated translation from DeepL
    - currently, ony fetching-per-entry is supported, the user specifically requests the translation for one piece of text, not the whole application
    - this way, the current translation can just be overridden

    example response:
    {
        "translations": [{
            "detected_source_language":"EN",
            "text":"Hallo, Welt!"
        }]
    }
'''
LANGUAGE_TERRITORIES = {
    'de' : 'DE',
    'en' : 'EN-US',
    'EN' : 'EN-US',
    'it' : 'IT',
    'nl' : 'NL',
    'fr' : 'FR',
}

class GetDeepLTranslation(MetaAppMixin, TemplateView):

    template_name = 'app_kit/ajax/get_translation.html'

    @method_decorator(csrf_exempt)
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_json_response_base(self):

        return {}


    def send_error_report_email(self, exception, error_message):

        subject = '[{0}] {1}'.format(self.__class__.__name__, error_message)

        tenant = self.meta_app.tenant
        tenant_admin_emails = tenant.get_admin_emails()
        tenant_text = 'Tenant schema: {0}. App uid: {1}. Admins: {2}.'.format(tenant.schema_name, self.meta_app.app.uid,
                                                    ','.join(tenant_admin_emails))
        
        text_content = '{0} \n\n Error type: {1} \n\n message: {2} \n\n {3}'.format(tenant_text, exception.__class__.__name__, error_message, traceback.format_exc())

        mail.mail_admins(subject, text_content)


    def get_translation(self, text, target_language):

        translation = None
        target_language = target_language.lower()
        success = False

        if target_language not in LANGUAGE_TERRITORIES:
            raise ValueError('DEEPL: Language territory not found for language code {0}'.format(target_language))

        language_with_territory = LANGUAGE_TERRITORIES[target_language]

        auth_key = settings.DEEPL_AUTH_KEY

        try:
            translator = deepl.Translator(auth_key)
            result = translator.translate_text(text, target_lang=language_with_territory)
            
        except Exception as e:
            self.send_error_report_email(e, 'DeepL error')
            raise e
        else:
            success = True
            translated_text = result.text


        result = {
            'translation' : translated_text,
            'success' : success,
        }

        return result
     

    def post(self, request, *args, **kwargs):

        text = request.POST.get('text', None)

        if text is None or len(text) == 0:
            return HttpResponseBadRequest("GetDeepLTranslation requires 'text' in POST data.")

        target_language = request.POST.get('target-language', None)

        if target_language is None or len(target_language) == 0:
            return HttpResponseBadRequest("GetDeepLTranslation requires 'target_language' in POST data.")
        
        result = self.get_translation(text, target_language)

        # return result as json
        return JsonResponse(result)


class TranslateVernacularNames(PagedTranslationFormMixin, MetaAppMixin, FormView):
    
    template_name = 'app_kit/translate_vernacular_names.html'
    form_class = TranslateVernacularNamesForm
    
    
    def form_valid(self, form):
        
        for language_code, translation_list in form.translations.items():

            for translation in translation_list:
                
                taxon = translation['taxon']
                name = translation['name']
                
                meta_vernacular_name = MetaVernacularNames.objects.filter(
                    language=language_code, taxon_source=taxon.taxon_source, name_uuid=taxon.name_uuid).first()

                if meta_vernacular_name:
                    if name:
                        meta_vernacular_name.name = name
                        meta_vernacular_name.save()
                        
                    else:
                        meta_vernacular_name.delete()
                
                else:
                    
                    if name:
                        meta_vernacular_name = MetaVernacularNames(
                            language=language_code,
                            taxon_source=taxon.taxon_source,
                            taxon_latname=taxon.taxon_latname,
                            taxon_author=taxon.taxon_author,
                            taxon_nuid=taxon.taxon_nuid,
                            name_uuid=taxon.name_uuid,
                            name=name,
                        )
                        
                        meta_vernacular_name.save()
            
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['saved'] = True
        return self.render_to_response(context)


'''
    APP BUILDING
    - covers validation, translation checking and the building process
    - the webpage shows the current progress of building an app:
      1. create content, 2. translate, 3. build,....
'''
class BuildApp(FormView):

    template_name = 'app_kit/build_app.html'
    form_class = BuildAppForm

    def dispatch(self, request, *args, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        if self.meta_app.build_settings:
            platforms = self.meta_app.build_settings.get('platforms', [])
            if platforms:
                initial['platforms'] = platforms

            distribution = self.meta_app.build_settings.get('distribution', 'appstores')
            initial['distribution'] = distribution

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['app_kit_mode'] = settings.APP_KIT_MODE
        
        app_release_builder = self.meta_app.get_release_builder()
        context['appbuilder'] = app_release_builder
        context['meta_app'] = self.meta_app

        site = get_current_site(self.request)
        context['app_kit_status'] = AppKitStatus.objects.filter(site=site).first()

        context['localcosmos_private'] = self.meta_app.get_global_option('localcosmos_private')

        # include review urls, if any present
        if not self.meta_app.published_version or self.meta_app.published_version != self.meta_app.current_version:
            context['aab_review_url'] = app_release_builder.aab_review_url(self.request)
            context['apk_review_url'] = app_release_builder.apk_review_url(self.request)
            
            context['browser_review_url'] = app_release_builder.browser_review_url(self.request)

            context['ipa_review_url'] = app_release_builder.ipa_review_url(self.request)
            
            context['pwa_zip_review_url'] = app_release_builder.browser_zip_review_url(self.request)

            app_kit_job = AppKitJobs.objects.filter(meta_app_uuid=self.meta_app.uuid,
                    app_version=self.meta_app.current_version, platform='ios', job_type='build').first()

            if app_kit_job:
                ios_status = app_kit_job.job_status
            else:
                ios_status = None
            context['ios_status'] = ios_status

        return context
    

    def form_valid(self, form):

        build_settings = {
            'platforms' : form.cleaned_data['platforms'],
            'distribution' : 'appstores', #form.cleaned_data['distribution'],
        }

        self.meta_app.build_settings = build_settings
        self.meta_app.save()

        action = self.kwargs['action']

        if action != 'validate' and settings.APP_KIT_MODE != 'live':
             return HttpResponseForbidden('Building is not allowed')

        # action can be: validate, translation complete, build
        app_release_builder = self.meta_app.get_release_builder()

        if action == 'release':
            # commercial installation check
            if self.request.user.is_superuser or LOCALCOSMOS_COMMERCIAL_BUILDER == False:
                release_result = app_release_builder.release()
            else:
                return HttpResponseForbidden('Releasing requires payment')
        else:

            def run_in_thread():

                # threading resets the connection -> set to tenant
                connection.set_tenant(self.request.tenant)
                
                if action == 'validate':
                    validation_result = app_release_builder.validate()
                elif action == 'build':
                    build_result = app_release_builder.build()

                close_old_connections()

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            

        context = self.get_context_data(**self.kwargs)
        
        return self.render_to_response(context)

        

class StartNewAppVersion(TemplateView):

    template_name = 'app_kit/start_new_app.html'

    def dispatch(self, request, *args, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_app'] = self.meta_app
        return context

    def post(self, request, *args, **kwargs):

        if self.meta_app.current_version == self.meta_app.published_version:
            new_version = self.meta_app.current_version + 1
            self.meta_app.current_version = new_version
            self.meta_app.build_number = None

            # reset status reports. otherwise the build page will show results of the last version
            self.meta_app.build_status = None
            self.meta_app.last_build_report = None

            self.meta_app.validation_status = None
            self.meta_app.last_validation_report = None

            self.meta_app.save()

            def run_in_thread():
                # threading resets the connection -> set to tenant
                connection.set_tenant(self.request.tenant)

                app_builder = self.meta_app.get_app_builder()
                app_builder.create_app_version()


                app_preview_builder = self.meta_app.get_preview_builder()
                app_preview_builder.build()

                delete_version = new_version - 2
                while delete_version > 0:
                    app_builder.delete_app_version(delete_version)
                    delete_version = delete_version - 1

                close_old_connections()
                
            thread = threading.Thread(target=run_in_thread)
            thread.start()

        
        content_type = ContentType.objects.get_for_model(self.meta_app)
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : content_type.id,
            'object_id' : self.meta_app.id,
        }
        return redirect(reverse('manage_metaapp', kwargs=url_kwargs))


class AddExistingGenericContent(FormView):

    template_name = 'app_kit/ajax/add_existing_generic_content.html'
    form_class = AddExistingGenericContentForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        self.generic_content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.meta_app, self.generic_content_type, **self.get_form_kwargs())


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_app'] = self.meta_app
        context['content_type'] = self.generic_content_type

        # check if it is a single content
        appbuilder = self.meta_app.get_preview_builder()
        ContentModel = self.generic_content_type.model_class()

        disallow_single_content = False
        feature_type = ContentModel.feature_type()
        if feature_type in appbuilder.single_content_features or feature_type == 'app_kit.features.taxon_profiles':
            disallow_single_content = True

        context['disallow_single_content'] = disallow_single_content
        context['content_model'] = ContentModel
        return context

    def form_valid(self, form):

        added_links = []

        for instance in form.cleaned_data['generic_content']:

            link = MetaAppGenericContent(
                meta_app=self.meta_app,
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.pk,
            )

            link.save()

            added_links.append(link)

        
        context=self.get_context_data(**self.kwargs)
        context['success'] = True
        context['form'] = form
        context['added_contents'] = form.cleaned_data['generic_content']
        context['added_links'] = added_links
        return self.render_to_response(context)


class ListManageApps(TemplateView):

    template_name = 'app_kit/list_manage_apps.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        app_content_type = ContentType.objects.get_for_model(MetaApp)

        context['content_type'] = app_content_type
        context['meta_apps'] = MetaApp.objects.all().order_by('pk')

        return context

'''
    GENERIC CONTENT MANAGEMENT CLASSES
'''

class RemoveAppGenericContent(AjaxDeleteView):

    model=MetaAppGenericContent
    template_name = 'app_kit/ajax/remove_app_generic_content.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_app'] = self.object.meta_app
        return context


from localcosmos_server.models import SecondaryAppLanguages
class ManageAppLanguages(TemplateView):

    template_name = 'app_kit/ajax/manage_app_languages.html'
    form_class = AddLanguageForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        self.language = kwargs.get('language', None)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_app'] = self.meta_app
        context['generic_content'] = self.meta_app
        context['content_type'] = ContentType.objects.get_for_model(MetaApp)
        context['languages'] = self.meta_app.languages()
        context['primary_language'] = self.meta_app.primary_language
        context['form'] = self.form_class()
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        action = kwargs['action']

        form = self.form_class()

        if action == 'add':

            form = self.form_class(request.POST)

            if form.is_valid():
                new_language = form.cleaned_data['language']
                # create the new locale
                locale, created = SecondaryAppLanguages.objects.get_or_create(app=self.meta_app.app,
                                                                              language_code=new_language)
        
        context['languages'] = self.meta_app.languages()
        context['primary_language'] = self.meta_app.primary_language
        context['form'] = form
        return self.render_to_response(context)



class DeleteAppLanguage(AjaxDeleteView):

    model = SecondaryAppLanguages
    template_name = 'app_kit/ajax/delete_app_language.html'

    def get_object(self):
        
        if 'pk' in self.kwargs:
            return self.model.objects.get(pk=self.kwargs["pk"])

        meta_app = MetaApp.objects.get(pk=self.kwargs['meta_app_id'])
        
        return self.model.objects.get(app=meta_app.app, language_code=self.kwargs['language'])


    def get_verbose_name(self):
        return self.object.language_code


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['language'] = obj.language_code
        return context

        
from localcosmos_server.taxonomy.views import ManageTaxonomicRestrictionsCommon
class AddTaxonomicRestriction(ManageTaxonomicRestrictionsCommon, FormView):
    template_name = 'localcosmos_server/taxonomy/taxonomic_restrictions.html'

    restriction_model = AppContentTaxonomicRestriction

    def get_taxon_search_url(self):
        return reverse('search_taxon')

    def get_availability(self):
        return True

    
class RemoveTaxonomicRestriction(AjaxDeleteView):

    model = AppContentTaxonomicRestriction

    def get_deletion_message(self):
        return _('Do you really want to remove {0}?'.format(self.object.taxon_latname))



'''
    Generic Content Images
'''

'''
    Save a content image from a ContentImageForm
'''
from localcosmos_server.view_mixins import ContentImageViewMixin
class ManageContentImageMixin(MetaAppMixin, ContentImageViewMixin):
    ContentImageClass = ContentImage
    ImageStoreClass = ImageStore
    LazyTaxonClass = LazyTaxon

    # cache the image
    def save_image(self, form):
        super().save_image(form)

        # add to cache
        release_builder = self.meta_app.get_release_builder()

        cache_path = release_builder._app_content_images_cache_path

        content_image_builder = ContentImageBuilder(cache_path)

        image_urls = content_image_builder.build_cached_images(self.content_image, force_build=True)

    '''
        optionally, an image can have a taxon assigned
    '''
    def set_taxon(self, request):
        self.taxon = None
        taxon_source = request.GET.get('taxon_source', None)
        taxon_latname = request.GET.get('taxon_latname', None)
        taxon_author = request.GET.get('taxon_author', None)

        if taxon_source and taxon_latname:
            models = TaxonomyModelRouter(taxon_source)
            taxon_instance = models.TaxonTreeModel.objects.filter(taxon_latname=taxon_latname,
                                                               taxon_author=taxon_author).first()

            if taxon_instance:
                self.taxon = self.LazyTaxonClass(instance=taxon_instance)
    


'''
    ajax view to fetch image suggestions, and save them
    in some cases, images reoccur, e.g. something like "circular" for Trait values
'''
class ManageContentImageSuggestions(TemplateView):

    template_name = 'app_kit/ajax/get_content_image_suggestions.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):

        self.content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        self.ModelClass = self.content_type.model_class()
        
        self.content_instance = None
        
        self.searchtext = request.GET.get('searchtext', '')
        
        if 'object_id' in kwargs:
            self.content_instance = self.content_type.get_object_for_this_type(pk=kwargs['object_id'])

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['image_suggestions'] = self.get_image_suggestions()
        return context


    def get_image_suggestions(self):

        if self.content_instance:
            if hasattr(self.content_instance, 'get_image_suggestions'):
                return self.content_instance.get_image_suggestions()
        else:
            if self.searchtext and len(self.searchtext) >= 3:
                return self.ModelClass.search_image_suggestions(self.searchtext)
            
        return []


from localcosmos_server.views import ManageContentImageBase
class ManageContentImage(ManageContentImageMixin, ManageContentImageBase, FormView):
    template_name = 'app_kit/ajax/content_image_form.html'

# manage multiple content images with preview
class ContentImagesList(MetaAppMixin, TemplateView):
    template_name = 'app_kit/ajax/content_images_list.html'
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        self.ModelClass = self.content_type.model_class()
        self.content_instance = self.content_type.get_object_for_this_type(pk=kwargs['object_id'])

        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_image_ctype'] = ContentType.objects.get_for_model(ContentImage)
        context['content_instance'] = self.content_instance
        return context


from app_kit.view_mixins import FormLanguageMixin
class ManageContentImageWithText(FormLanguageMixin, ManageContentImage):

    form_class = ManageContentImageWithTextForm
    template_name = 'app_kit/ajax/content_image_with_text_form.html'

    def set_primary_language(self):
        meta_app = MetaApp.objects.get(pk=self.kwargs['meta_app_id'])
        self.primary_language = meta_app.primary_language


class ManageContentImagesWithText(ManageContentImageWithText):
    template_name = 'app_kit/ajax/content_images_with_text_form.html'


class ManageLocalizedContentImage(LicencingFormViewMixin, FormView):

    form_class = ManageLocalizedContentImageForm
    template_name = 'app_kit/ajax/localized_content_image_form.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_content_image(*args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_new_image_store(self):
        image_store = ImageStore(
            uploaded_by = self.request.user,
        )

        return image_store


    def set_content_image(self, **kwargs):
        
        self.content_image = ContentImage.objects.get(pk=kwargs['content_image_id'])
        self.language_code = kwargs['language_code']

        self.localized_content_image = LocalizedContentImage.objects.filter(content_image=self.content_image,
                                                                language_code=self.language_code).first()

        self.licence_registry_entry = None
        if self.localized_content_image:
            self.set_licence_registry_entry(self.localized_content_image.image_store, 'source_image')


    def get_initial(self):
        initial = super().get_initial()

        if self.localized_content_image:
            # file fields cannot have an initial value [official security feature of all browsers]
            initial['crop_parameters'] = self.localized_content_image.crop_parameters
            initial['features'] = self.localized_content_image.features
            initial['source_image'] = self.localized_content_image.image_store.source_image
            # make the hidden fields of the form valid
            initial['image_type'] = self.content_image.image_type
            initial['text'] = self.content_image.text


            licencing_initial = self.get_licencing_initial()
            initial.update(licencing_initial)

        return initial

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['content_instance'] = self.content_image.content
        if self.localized_content_image:
            form_kwargs['current_image'] = self.localized_content_image.image_store.source_image
        return form_kwargs

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['localized_content_image'] = self.localized_content_image
        context['language_code'] = self.language_code
        context['content_image'] = self.content_image

        return context

    def form_valid(self, form):
        
        # first, store the image in the imagestore
        if not self.localized_content_image:
            image_store = self.get_new_image_store()

        else:
            # check if the image has changed
            current_image_store = self.localized_content_image.image_store

            if current_image_store.source_image != form.cleaned_data['source_image']:
                image_store = self.get_new_image_store()
            else:
                image_store = current_image_store

        image_store.source_image = form.cleaned_data['source_image']
        image_store.md5 = form.cleaned_data['md5']

        image_store.save()


        # store the link between ImageStore and Content in ContentImage
        if not self.localized_content_image:
            
            self.localized_content_image = LocalizedContentImage(
                content_image = self.content_image,
                language_code = self.language_code,
            )

        self.localized_content_image.image_store = image_store

        # crop_parameters are optional in the db
        # this makes sense because SVGS might be uploaded
        self.localized_content_image.crop_parameters = form.cleaned_data.get('crop_parameters', None)

        # features are optional in the db
        self.localized_content_image.features = form.cleaned_data.get('features', None)

        self.localized_content_image.save()

        self.register_content_licence(form, self.localized_content_image.image_store, 'source_image')

        context = self.get_context_data(**self.kwargs)
        context['form'] = form

        return self.render_to_response(context)



class DeleteContentImage(MetaAppMixin, AjaxDeleteView):
    
    template_name = 'app_kit/ajax/delete_content_image.html'
    model = ContentImage

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['image_type'] = self.object.image_type
        context['content_instance'] = self.object.content
        return context


class DeleteContentImages(MetaAppMixin, AjaxDeleteView):
    
    template_name = 'app_kit/ajax/delete_content_images.html'
    model = ContentImage

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['image_type'] = self.object.image_type
        context['content_instance'] = self.object.content
        context['content_image_id'] = self.object.id
        return context



class DeleteLocalizedContentImage(AjaxDeleteView):
    
    template_name = 'app_kit/ajax/delete_localized_content_image.html'
    model = LocalizedContentImage

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_image'] = self.object.content_image
        context['language_code'] = self.object.language_code
        return context


class MockButton(TemplateView):
    
    template_name = 'app_kit/ajax/mockbutton.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = self.request.GET.get('message', '')
        return context


'''
    Spreadsheet import
    - upload should display a progress bar, there might be many images
'''
import zipfile, os, shutil

class ImportFromZip(MetaAppMixin, FormView):

    template_name = 'app_kit/ajax/zip_import.html'
    form_class = ZipImportForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        self.generic_content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        Model = self.generic_content_type.model_class()
        self.generic_content = Model.objects.get(pk=kwargs['generic_content_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['generic_content'] = self.generic_content
        context['content_type'] = self.generic_content_type
        context['form_valid'] = False
        return context        


    def form_valid(self, form):

        # temporarily save the zipfile
        zip_file = form.cleaned_data['zipfile']

        zip_filename = '{0}.zip'.format( str(self.generic_content.uuid) )
        zip_destination_dir = os.path.join(settings.APP_KIT_TEMPORARY_FOLDER, str(self.generic_content.uuid))

        if os.path.isdir(zip_destination_dir):
            shutil.rmtree(zip_destination_dir)

        os.makedirs(zip_destination_dir)

        zip_destination_path = os.path.join(zip_destination_dir, zip_filename)
        
        with open(zip_destination_path, 'wb+') as zip_destination:
            for chunk in zip_file.chunks():
                zip_destination.write(chunk)

        # unzip zipfile
        unzip_path = os.path.join(settings.APP_KIT_TEMPORARY_FOLDER, str(self.generic_content.uuid), 'contents')

        if os.path.isdir(unzip_path):
            shutil.rmtree(unzip_path)

        os.makedirs(unzip_path)
        
        with zipfile.ZipFile(zip_destination_path, 'r') as zip_file:
            zip_file.extractall(unzip_path)
            

        def run_in_thread():

            # threading resets the connection -> set to tenant
            connection.set_tenant(self.request.tenant)

            self.generic_content.lock('zip_import')

            try:
                ignore_nonexistent_images = form.cleaned_data['ignore_nonexistent_images']
                
                # validate the zipfile, then import, maybe use threading in form_valid
                zip_importer = self.generic_content.zip_import_class(self.request.user, self.generic_content,
                                                                     unzip_path, ignore_nonexistent_images=ignore_nonexistent_images)
                zip_is_valid = zip_importer.validate()

                if zip_is_valid == True:
                    zip_importer.import_generic_content()

                # store errors in self.generic_content.messages
                self.generic_content.messages['last_zip_import_errors'] = [str(error) for error in zip_importer.errors]

                # unlock saves messages
                self.generic_content.unlock()

                # remove zipfile and unzipped
                shutil.rmtree(unzip_path)
                shutil.rmtree(zip_destination_dir)

                close_old_connections()
                
            
            except Exception as e:

                self.generic_content.messages['last_zip_import_errors'] = [str(e)]

                # unlock generic content
                self.generic_content.unlock()

                # remove zipfile and unzipped
                shutil.rmtree(unzip_path)
                shutil.rmtree(zip_destination_dir)

                # send error email
                raise e

        # run validation and import in thread
        thread = threading.Thread(target=run_in_thread)
        thread.start()

        context = self.get_context_data(**self.kwargs)
        context['form'] = form

        context['form_valid'] = True

        return self.render_to_response(context)



class TagsMixin:

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_content_object(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_content_object(self, **kwargs):
        self.content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        self.content_object = self.content_type.get_object_for_this_type(pk=self.kwargs['object_id'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = self.content_type
        context['content_object'] = self.content_object
        return context

class TagAnyElement(TagsMixin, FormView):

    form_class = TagAnyElementForm
    template_name = 'app_kit/ajax/tag_any_element.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['tags'] = self.content_object.tags.all()
        return initial

    def form_valid(self, form):
        old_tags = [tag.name.lower() for tag in self.content_object.tags.all()]
        new_tags = form.cleaned_data['tags']

        for tag in new_tags:
            tag = tag.lower()
            if tag in old_tags:
                del old_tags[old_tags.index(tag)]
            else:
                self.content_object.tags.add(tag)
        
        for tag in old_tags:
            self.content_object.tags.remove(tag)

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)


class ReloadTags(TagsMixin, TemplateView):

    template_name = 'app_kit/ajax/tags.html'


class ChangeGenericContentPublicationStatus(MetaAppMixin, FormView):

    form_class = GenericContentStatusForm
    template_name = 'app_kit/ajax/change_generic_content_status.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_generic_content_link(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_generic_content_link(self, **kwargs):
        self.generic_content_link = MetaAppGenericContent.objects.get(pk=kwargs['generic_content_link_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['generic_content_link'] = self.generic_content_link
        context['success'] = False
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['publication_status'] = self.generic_content_link.publication_status
        return initial

    def form_valid(self, form):

        if not self.generic_content_link.options:
            self.generic_content_link.options = {}

        self.generic_content_link.options['publication_status'] = form.cleaned_data['publication_status']
        self.generic_content_link.save()

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)


class ManageObjectOrder(TemplateView):

    template_name = 'app_kit/ajax/manage_object_order.html'
    
    def get_queryset(self):
        return self.model.objects.all()
    
    def get_container_id(self):
        return 'order-ctype-{0}-container'.format(self.content_type.id)

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_order_objects(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_order_objects(self, **kwargs):
        self.content_type = ContentType.objects.get(pk=kwargs['content_type_id'])
        self.model = self.content_type.model_class()
        self.order_objects = self.get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_objects'] = self.order_objects
        context['content_type'] = self.content_type
        context['container_id'] = self.get_container_id()
        return context

class ManageAppKitSeoParameters(MetaAppFormLanguageMixin, ManageSeoParameters):
    
    template_name = 'app_kit/ajax/manage_seo_parameters.html'
    seo_model_class = AppKitSeoParameters

# LEGAL
class IdentityMixin:

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['identity'] = settings.APP_KIT_LEGAL_NOTICE['identity']
        return context

    
class LegalNotice(IdentityMixin, TemplateView):

    template_name = 'app_kit/legal/legal_notice.html'

    @method_decorator(csrf_exempt)
    @method_decorator(requires_csrf_token)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class PrivacyStatement(IdentityMixin, TemplateView):

    template_name = 'app_kit/legal/privacy_statement.html'

    @method_decorator(csrf_exempt)
    @method_decorator(requires_csrf_token)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

from django.conf import settings
from django import forms
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from .models import (MetaAppGenericContent, LOCALIZED_CONTENT_IMAGE_TRANSLATION_PREFIX, LocalizedContentImage,
                    ContentImage)

from app_kit.generic import PUBLICATION_STATUS

from localcosmos_server.widgets import TwoStepFileInput
from localcosmos_server.forms import LocalizeableForm
from localcosmos_server.models import App

from app_kit.appbuilder.AppBuilderBase import AppBuilderBase

from taxonomy.models import MetaVernacularNames
from taxonomy.lazy import LazyTaxon

import base64, math, uuid

from .definitions import TEXT_LENGTH_RESTRICTIONS

from django_tenants.utils import get_tenant_model, get_tenant_domain_model
Domain = get_tenant_domain_model()
Tenant = get_tenant_model()

RESERVED_SUBDOMAINS = getattr(settings, 'RESERVED_SUBDOMAINS', [])

class CleanAppSubdomainMixin:

    def clean_subdomain(self):

        subdomain = self.cleaned_data['subdomain']
        subdomain = subdomain.strip().lower()

        try:
            subdomain.encode('ascii')
        except:
            raise forms.ValidationError(_('Use only [a-z] and [0-9] for the subdomain.') )

        if subdomain in RESERVED_SUBDOMAINS:
            raise forms.ValidationError(_('This subdomain is forbidden.'))

        if not subdomain[0].isalpha():
            raise forms.ValidationError(_('The subdomain has to start with a letter.'))

        if not subdomain.isalnum():
            raise forms.ValidationError(_('The subdomain has to be alphanumeric.'))

        if Domain.objects.filter(domain__startswith=subdomain, app__isnull=False).exists():
            raise forms.ValidationError(_('This subdomain already exists.'))

        # the tenant has to exist prior creating the app. Domain has a FK to App and Tenant
        #if Tenant.objects.filter(schema_name = subdomain).exists():
        #    raise forms.ValidationError(_('This subdomain already exists.'))
        
        return subdomain

'''
    CreateAppForm
    - is only used for creating an app on the commercial local cosmos
'''
LANGUAGE_CHOICES = tuple(sorted(settings.LANGUAGES, key=lambda item: item[1]))
class CreateAppForm(CleanAppSubdomainMixin, forms.Form):

    name = forms.CharField(max_length=255, label=_('Name of your app'), required=True,
                           help_text=_('In the primary language'))
    
    primary_language = forms.ChoiceField(choices=LANGUAGE_CHOICES,
                            help_text=_('The language the app is created in. Translations can be made later.'))

    frontend = forms.ChoiceField(choices=[], required=True, initial=settings.APP_KIT_DEFAULT_FRONTEND)
    
    subdomain = forms.CharField(max_length=255, required=True,
                    help_text=_('Your app will be available at subdomain.localcosmos.org, where "subdomain" is the name you configured here.'))

    def __init__(self, *args, **kwargs):
        
        allow_uuid = kwargs.pop('allow_uuid', False)
        
        super().__init__(*args, **kwargs)

        self.fields['frontend'].choices = self.get_frontend_choices()
        
        if allow_uuid == True:
            self.fields['uuid'] = forms.UUIDField(required=False)


    def get_frontend_choices(self):

        installed_frontends = AppBuilderBase.get_installed_frontends()
        choices = []

        for frontend_name in installed_frontends:
            choice = (frontend_name, frontend_name)
            choices.append(choice)

        return choices
                
    
    def clean_name(self):
        name = self.cleaned_data['name']

        if App.objects.filter(name=name).exists() == True:
            del self.cleaned_data['name']
            raise forms.ValidationError(_('An app with this name already exists.'))

        return name



# language is always the primary language
class CreateGenericContentForm(LocalizeableForm):
    name = forms.CharField(max_length=TEXT_LENGTH_RESTRICTIONS['GenericContent']['name'])
    content_type_id = forms.IntegerField(widget=forms.HiddenInput)

    localizeable_fields = ['name']


LANGUAGE_CHOICES =  [('',_('Select language'))] + list(settings.LANGUAGES)
            
class AddLanguageForm(forms.Form):
    language = forms.ChoiceField(choices=LANGUAGE_CHOICES)

'''
    ContentImageForms
    do not delete these imports as they are referenced throughout app_kit
'''
from localcosmos_server.forms import (ManageContentImageForm, ManageContentImageWithTextForm,
    ManageLocalizedContentImageForm, OptionalContentImageForm)
    

class GenericContentOptionsForm(forms.Form):

    instance_fields = []
    global_options_fields = []

    def __init__(self, *args, **kwargs):

        initial = kwargs.pop('initial', {})
        self.generic_content = kwargs.pop('generic_content')
        self.meta_app = kwargs.pop('meta_app')

        self.primary_language = self.meta_app.primary_language

        if self.generic_content.global_options:
            global_options = self.generic_content.global_options
        else:
            global_options = {}
        
        options = self.generic_content.options(self.meta_app)

        if options:
            for key, value in options.items():

                if key in self.instance_fields:
                    initial[key] = value['uuid']
                else:
                    initial[key] = value

        if global_options:
            for key, value in global_options.items():

                if key in self.instance_fields:
                    initial[key] = value['uuid']
                else:
                    initial[key] = value

        self.uuid_to_instance = {}
                    
        super().__init__(initial=initial, *args, **kwargs)


class EditGenericContentNameForm(LocalizeableForm):

    localizeable_fields = ['name', 'description']

    content_type_id = forms.IntegerField(widget=forms.HiddenInput)
    generic_content_id = forms.IntegerField(widget=forms.HiddenInput)
    name = forms.CharField(max_length=TEXT_LENGTH_RESTRICTIONS['GenericContent']['name'])

    description = forms.CharField(widget=forms.Textarea, required=False)


class AddExistingGenericContentForm(forms.Form):

    generic_content = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=None)

    def __init__(self, meta_app, content_type, *args, **kwargs):
        super().__init__(*args, **kwargs)

        app_existing_content = MetaAppGenericContent.objects.filter(meta_app=meta_app,
                                                                    content_type=content_type)

        FeatureModel=content_type.model_class()

        addable_content = FeatureModel.objects.filter(primary_language=meta_app.primary_language).exclude(
            pk__in=app_existing_content.values_list('object_id', flat=True))

        self.has_choices = addable_content.count()

        self.fields['generic_content'].queryset = addable_content
        self.fields['generic_content'].label = FeatureModel._meta.verbose_name

        
class MetaAppOptionsForm(GenericContentOptionsForm):

    global_options_fields = ['allow_user_create_matrices', 'allow_anonymous_observations',
                             'localcosmos_private', 'localcosmos_private_api_url', 'version']
    
    allow_anonymous_observations = forms.BooleanField(required=False,
                        label=_('Allow unregistered users to report observations'),
                        help_text=_('Only applies if your app contains observation forms.'))


    localcosmos_private = forms.BooleanField(label=_('Local Cosmos Private'),
                                help_text=_('I run my own Local Cosmos Server'), required=False)
    localcosmos_private_api_url = forms.CharField(label=_('API URL of your private Local Cosmos Server'),
                                                help_text=_('Only applies if you run your own Local Cosmos Server.'),
                                                required=False)
    
    version = forms.CharField(max_length=30, required=False, help_text = _('Manually set the version of your app.'))



class TranslateAppForm(forms.Form):

    page_size = 30

    def __init__(self, meta_app, *args, **kwargs):
        self.meta_app = meta_app

        self.page = kwargs.pop('page', 1)
        
        super().__init__(*args, **kwargs)
        
        self.primary_locale = self.meta_app.localizations[self.meta_app.primary_language]
        all_items = list(self.primary_locale.items())
        all_items_count = len(all_items)

        self.total_pages = math.ceil(all_items_count / self.page_size)
        self.pages = range(1, self.total_pages+1)
        
        start = ((self.page-1) * self.page_size)
        end = self.page * self.page_size
        if end > all_items_count:
            end = all_items_count

        page_items = list(self.primary_locale.items())[start:end]

        self.meta = self.primary_locale.get('_meta', {})

        for key, primary_language_value in page_items:

            language_independant_identifier = uuid.uuid4()

            languages = meta_app.secondary_languages()

            translation_complete = True

            fieldset = []

            for counter, language_code in enumerate(languages, 1):

                if key == '_meta':
                    continue

                to_locale = self.meta_app.localizations.get(language_code, {})

                # b64 encode the source key to make it a valid html field name attribute
                field_name_utf8 = '{0}-{1}'.format(language_code, key)

                field_name = base64.b64encode(field_name_utf8.encode()).decode()

                if key.startswith(LOCALIZED_CONTENT_IMAGE_TRANSLATION_PREFIX) == True:

                    # get initial, LocalizedContentImage
                    content_type = ContentType.objects.get(pk=primary_language_value['content_type_id'])
                    object_id = primary_language_value['object_id']
                    image_type = primary_language_value['image_type']
                    content_image = ContentImage.objects.filter(content_type=content_type, object_id=object_id,
                                        image_type=image_type).first()

                    if content_image:

                        primary_language_image_url = primary_language_value['media_url']

                        localized_content_image = LocalizedContentImage.objects.filter(content_image=content_image,
                                                                                    language_code=language_code).first()

                        url_kwargs = {
                            'content_image_id' : content_image.id,
                            'language_code' : language_code,
                        }
                        
                        url = reverse('manage_localized_content_image', kwargs=url_kwargs)
                        image_container_id = 'localized_content_image_{0}_{1}'.format(content_image.id, language_code)

                        widget_kwargs = {
                            'instance' : localized_content_image,
                            'url' : url,
                            'image_container_id' : image_container_id,
                        }

                        widget = TwoStepFileInput(**widget_kwargs)

                        field = forms.ImageField(label=_('Image'), widget=widget, required=False)
                        field.primary_language_image_url = primary_language_image_url
                        field.is_image = True

                else:

                    initial = to_locale.get(key, None)
                    if initial == None:
                        translation_complete = False
                    
                    widget = forms.TextInput

                    if len(primary_language_value) > 50 or (key in self.meta and 'layoutability' in self.meta[key]):
                        widget = forms.Textarea            
                
                    field = forms.CharField(widget=widget, label=primary_language_value, initial=initial,
                                            required=False)

                    field.is_image = False
                    field.language_independant_identifier = language_independant_identifier
                    
                field.language = language_code
                field.is_first = False
                field.is_last = False

                if key in self.meta and 'layoutability' in self.meta[key]:
                    field.layoutability = self.meta[key]['layoutability']

                if counter == 1:
                    field.is_first = True

                if counter == len(languages):
                    field.is_last = True

                fieldset_entry = {
                    'field_name' : field_name,
                    'field' : field,
                }
                fieldset.append(fieldset_entry)
                #self.fields[field_name] = field

            if translation_complete == True:
                for field_entry in fieldset:
                    self.fields[field_entry['field_name']] = field_entry['field']

            else:
                fieldset.reverse()

                field_order = []
                
                for field_entry in fieldset:
                    self.fields[field_entry['field_name']] = field_entry['field']
                    field_order.insert(0, field_entry['field_name'])

                self.order_fields(field_order)
        

    def clean(self):
        # make decoded translations available
        self.translations = {}

        # value can be a file/image
        for b64_key, value in self.cleaned_data.items():

            if value is not None and len(value) > 0:
                field_name = base64.b64decode(b64_key).decode()

                parts = field_name.split('-')
                language = parts[0]
                key = '-'.join(parts[1:])                

                if language not in self.translations:
                    self.translations[language] = {}

                self.translations[language][key] = value
            
        return self.cleaned_data



PLATFORM_CHOICES = [(platform, platform) for platform in settings.APP_KIT_SUPPORTED_PLATFORMS]
DISTRIBUTION_CHOICES = (
    ('ad-hoc', _('ad-hoc')),
    ('appstores', _('App Stores')),
)
class BuildAppForm(forms.Form):

    platforms = forms.MultipleChoiceField(label=_('Platforms'), choices=PLATFORM_CHOICES,
                widget=forms.CheckboxSelectMultiple, initial=[c[0] for c in PLATFORM_CHOICES], required=True)
    '''
    #distribution = forms.ChoiceField(label=_('Distribution'), choices=DISTRIBUTION_CHOICES,
    #                    initial='appstores', help_text=_('Ad-hoc is android only. iOS is not supported.'))

    def clean(self):
        platforms = self.cleaned_data.get('platforms', [])
        #distribution = self.cleaned_data['distribution']

        #if distribution == 'ad-hoc' and 'ios' in platforms:
        #    raise forms.ValidationError(_('Ad-hoc distribution is not available for the iOS platform.'))
        
        return self.cleaned_data
    '''

from django.core.validators import FileExtensionValidator
class ZipImportForm(forms.Form):
    zipfile = forms.FileField(validators=[FileExtensionValidator(allowed_extensions=['zip'])])
    ignore_nonexistent_images = forms.BooleanField(label=_('Ignore non-existent images'), required=False,
                        help_text=_('If checked, the import will ignore images that are not in the zip file.'))

from taggit.forms import TagField
class TagAnyElementForm(forms.Form):

    tags = TagField(required=False)



class GenericContentStatusForm(forms.Form):
    publication_status = forms.ChoiceField(choices=PUBLICATION_STATUS)


class TranslateVernacularNamesForm(forms.Form):
    
    page_size = 30
    
    def __init__(self, meta_app, *args, **kwargs):
        self.meta_app = meta_app
        
        self.page = kwargs.pop('page', 1)
        
        super().__init__(*args, **kwargs)
        
        app_vernacular_names = meta_app.get_meta_vernacular_names(languages=[meta_app.primary_language])
                
        app_vernacular_names_count = len(app_vernacular_names)
                
        self.total_pages = math.ceil(app_vernacular_names_count / self.page_size)
        self.pages = range(1, self.total_pages+1)
        
        start = ((self.page-1) * self.page_size)
        end = self.page * self.page_size
        if end > app_vernacular_names_count:
            end = app_vernacular_names_count

        page_items = app_vernacular_names[start:end]
        
        languages = meta_app.secondary_languages()
        
        for vernacular_name in page_items:

            language_independant_identifier = uuid.uuid4()
            
            lazy_taxon = LazyTaxon(instance=vernacular_name)

            translation_complete = True

            fieldset = []
            
            field_label = vernacular_name.name

            for counter, language_code in enumerate(languages, 1):

                to_locale = MetaVernacularNames.objects.filter(taxon_source=vernacular_name.taxon_source,
                    name_uuid=vernacular_name.name_uuid, language=language_code).first()
                
                initial = None
                
                if to_locale:
                    initial = to_locale.name
                else:
                    translation_complete = False
                
                field_name = 'mvn-{0}-{1}'.format(vernacular_name.pk, language_code)
                
                widget = forms.TextInput          
            
                field = forms.CharField(widget=widget, label=field_label, initial=initial,
                                        required=False)

                field.language_independant_identifier = language_independant_identifier
                
                field.language = language_code
                field.taxon = lazy_taxon
                field.is_first = False
                field.is_last = False

                if counter == 1:
                    field.is_first = True

                if counter == len(languages):
                    field.is_last = True

                fieldset_entry = {
                    'field_name' : field_name,
                    'field' : field,
                }
                fieldset.append(fieldset_entry)
                
                
            if translation_complete == True or str(vernacular_name.name_uuid):
                for field_entry in fieldset:
                    self.fields[field_entry['field_name']] = field_entry['field']

            else:
                fieldset.reverse()

                field_order = []
                
                for field_entry in fieldset:
                    self.fields[field_entry['field_name']] = field_entry['field']
                    field_order.insert(0, field_entry['field_name'])

                self.order_fields(field_order)
                
    def clean(self):
        # make decoded translations available
        self.translations = {}
        
        for field_name, field in self.fields.items():
            
            translation = {
                'taxon': self.fields[field_name].taxon,
                'name': None,
            }
            
            language = field.language
            if language not in self.translations:
                self.translations[language] = []
            
            if field_name in self.cleaned_data:
                
                value = self.cleaned_data.get(field_name, None)

                if value is not None and len(value) > 0:  
                    translation['name'] = value

            self.translations[language].append(translation)
            
        return self.cleaned_data
        
        
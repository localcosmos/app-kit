from django.conf import settings
from django import forms
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from .models import (MetaAppGenericContent, LOCALIZED_CONTENT_IMAGE_TRANSLATION_PREFIX, LocalizedContentImage,
                    ContentImage)

from localcosmos_server.widgets import (TwoStepFileInput, HiddenJSONInput)
from localcosmos_server.forms import LocalizeableForm, FormLocalizationMixin
from localcosmos_server.models import App

import hashlib, base64, math

from .definitions import TEXT_LENGTH_RESTRICTIONS

import os

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
    
    subdomain = forms.CharField(max_length=255, required=True,
                    help_text=_('Your app will be available at subdomain.localcosmos.org, where "subdomain" is the name you configured here.'))

    def __init__(self, *args, **kwargs):
        
        allow_uuid = kwargs.pop('allow_uuid', False)
        
        super().__init__(*args, **kwargs)
        
        if allow_uuid == True:
            self.fields['uuid'] = forms.UUIDField(required=False)
                
    
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


from localcosmos_server.forms import ManageContentImageFormCommon
from content_licencing.mixins import LicencingFormMixin, OptionalLicencingFormMixin
'''
    A form with a required, licenced ContentImage
'''
class ManageContentImageForm(ManageContentImageFormCommon, LicencingFormMixin):
    
    # cropping
    crop_parameters = forms.CharField(widget=forms.HiddenInput)

    # features like arrows
    features = forms.CharField(widget=HiddenJSONInput, required=False)

    # image_type
    image_type = forms.CharField(widget=forms.HiddenInput, required=False)

    # md5
    md5 = forms.CharField(widget=forms.HiddenInput, required=False)

    requires_translation = forms.BooleanField(required=False)
    

    def clean_source_image(self):

        source_image = self.cleaned_data.get('source_image')
        if not source_image and not self.current_image:
            raise forms.ValidationError('An image file is required.')

        return source_image
    


class ManageContentImageWithTextForm(FormLocalizationMixin, ManageContentImageForm):

    input_language = forms.CharField(widget=forms.HiddenInput)

    text = forms.CharField(max_length=355, required=False, widget=forms.Textarea,
                           help_text=_('Text that will be shown together with this image.'))

    localizeable_fields = ['text']
    layoutable_simple_fields = ['text']


class ManageLocalizedContentImageForm(ManageContentImageForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['requires_translation']


'''
    A form with an optional ContentImage. If the user uploads an image, creator_name and licence have to be present
'''
class OptionalContentImageForm(ManageContentImageFormCommon, OptionalLicencingFormMixin):

    # cropping
    crop_parameters = forms.CharField(widget=forms.HiddenInput, required=False)

    # features like arrows
    features = forms.CharField(widget=HiddenJSONInput, required=False)

    # image_type
    image_type = forms.CharField(widget=forms.HiddenInput, required=False)

    # md5
    md5 = forms.CharField(widget=forms.HiddenInput, required=False)

    # if suggested images are provided, the user may click on the suggested image
    referred_content_image_id = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def fields_required(self, fields):
        """Used for conditionally marking fields as required."""
        for field in fields:
            if not self.cleaned_data.get(field, None):
                msg = forms.ValidationError(_('This field is required.'))
                self.add_error(field, msg)


    # if an image is present, at least crop_parameters, licence and creator_name have to be present
    def clean(self):
        cleaned_data = super().clean()
        file_ = cleaned_data.get('source_image', None)

        if file_ is not None:
            self.fields_required(['creator_name', 'licence'])
            
        
        return cleaned_data
    

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

    localizeable_fields = ['name']

    content_type_id = forms.IntegerField(widget=forms.HiddenInput)
    generic_content_id = forms.IntegerField(widget=forms.HiddenInput)
    name = forms.CharField(max_length=TEXT_LENGTH_RESTRICTIONS['GenericContent']['name'])


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
                             'localcosmos_private', 'localcosmos_private_api_url']

    '''
    allow_user_create_matrices = forms.BooleanField(required=False,
                        label=_('allow the user to create his own button matrices'),
                        help_text=_('only applies if your app contains at least one Button Matrix'))
    '''
    allow_anonymous_observations = forms.BooleanField(required=False,
                        label=_('Allow unregistered users to report observations'),
                        help_text=_('Only applies if your app contains observation forms.'))


    localcosmos_private = forms.BooleanField(label=_('Local Cosmos Private'),
                                help_text=_('I run my own Local Cosmos Server'), required=False)
    localcosmos_private_api_url = forms.CharField(label=_('API URL of your private Local Cosmos Server'),
                                                help_text=_('Only applies if you run your own Local Cosmos Server.'),
                                                required=False)



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

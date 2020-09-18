from django.conf import settings
from django import forms
from django.conf import settings
from django.apps import apps
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from django_countries.fields import CountryField

from localcosmos_server.slugifier import create_unique_slug

from .models import MetaAppGenericContent

from localcosmos_server.widgets import (CropImageInput, ImageInputWithPreview, AjaxFileInput,
                                        TwoStepDiskFileInput)
from localcosmos_server.forms import LocalizeableForm
from localcosmos_server.models import App

import hashlib, base64, math

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

    # image_type
    image_type = forms.CharField(widget=forms.HiddenInput, required=False)

    # md5
    md5 = forms.CharField(widget=forms.HiddenInput, required=False)
    

    def clean_source_image(self):

        source_image = self.cleaned_data.get('source_image')
        if not source_image and not self.current_image:
            raise forms.ValidationError('An image file is required.')

        return source_image
    


class ManageContentImageWithTextForm(ManageContentImageForm):
    text = forms.CharField(max_length=355, required=False,
                           help_text=_('Text that will be shown together with this image.'))
    
'''
    A form with an optional ContentImage. If the user uploads an image, creator_name and licence have to be present
'''
class OptionalContentImageForm(ManageContentImageFormCommon, OptionalLicencingFormMixin):

    # cropping
    crop_parameters = forms.CharField(widget=forms.HiddenInput, required=False)

    # image_type
    image_type = forms.CharField(widget=forms.HiddenInput, required=False)

    # md5
    md5 = forms.CharField(widget=forms.HiddenInput, required=False)

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



'''
    App Design and texts
    - the fields are loaded from the theme config file
    - image fields have to be optional, they are handled via ajax. the form has to validate without images,
      otherwise it would not be processed by ViewClass.form_valid()
'''
def ratio_to_css_class(ratio):
    css_class = 'ratio-{0}'.format(ratio.replace(':','x'))
    return css_class


'''
    AppThemeImages
    - are not stored in the ImageStore and are no ContentImages
    - The AppThemeImages are stored on disk, in the preview folder of the current app version
'''
from .AppThemeImage import AppThemeImage
class GetAppThemeImageFormFieldMixin:

    # image_type is the type name of the image as declared in the theme settings
    def get_image_form_field(self, image_type, definition):

        app_content_type = ContentType.objects.get_for_model(self.meta_app)
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'image_type' : image_type,
        }

        app_theme_image = AppThemeImage(self.meta_app, image_type)
            
        upload_image_url = reverse('manage_app_theme_image', kwargs=url_kwargs)

        help_text = definition.get('help_text', None)
        if help_text:
            help_text = _(help_text)

        extra_css_classes = ''

        if 'ratio' in definition['restrictions']:
            extra_css_classes = ratio_to_css_class(definition['restrictions']['ratio'])
        else:
            extra_css_classes = 'background-contains'

        delete_url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'image_type' : image_type,
        }

        delete_url = reverse('delete_app_theme_image', kwargs=delete_url_kwargs)

        widget=TwoStepDiskFileInput(url=upload_image_url, instance=app_theme_image, delete_url=delete_url,
                                    extra_css_classes=extra_css_classes)

        # apply the restrictions, like file type, ratio etc as a validator for the ImageField
        validators = []

        for restriction_type, restriction in definition['restrictions'].items():
            ValidatorClass = VALIDATOR_CLASS_MAP[restriction_type]
            validator = ValidatorClass(restriction)
            validators.append(validator)

        form_field = SVGandImageField(widget=widget, help_text=help_text, required=False, validators=validators)

        # do not use .required. Form should be valid without images - app validation is done during build
        is_required = definition.get('required', False)
        form_field.is_required = is_required
        

        return form_field
        

class AppDesignForm(GetAppThemeImageFormFieldMixin, forms.Form):

    theme = forms.ChoiceField()
    input_language = forms.CharField(widget=forms.HiddenInput)
    localizeable_fields = []

    legal_notice_fields = {
        'entity_name' : forms.CharField(label=_('Name of entity'), required=False,
            help_text=_('First- and Surname if you are an individual. Otherwise the name of the legal entity.')),
        'street' : forms.CharField(label=_('Street'), required=False),
        'zip_code' : forms.CharField(label=_('Zip code'), required=False),
        'city' : forms.CharField(label=_('City'), required=False),
        'country' : CountryField().formfield(),
        'email' : forms.EmailField(label=_('Email'), required=False),
        'phone' : forms.CharField(label=_('Phone'), required=False),
    }


    def __init__(self, meta_app, *args, **kwargs):
        
        self.meta_app = meta_app
        self.language = kwargs.pop('language', meta_app.primary_language)
        self.active_theme = self.meta_app.get_theme()

        initial = kwargs.pop('initial', {})        

        initial['theme'] = self.active_theme.name

        super().__init__(initial=initial, *args, **kwargs)

        appbuilder = meta_app.get_preview_builder()

        theme_choices = []
        
        for theme in appbuilder.available_themes():

            choice = (theme.name, theme.name)
            theme_choices.append(choice)


        self.fields['theme'].choices = theme_choices

        # IMAGES, initial not possible
        for image_type, definition in sorted(self.active_theme.user_content['images'].items()):
            image_form_field = self.get_image_form_field(image_type, definition)
            self.fields[image_type] = image_form_field
            
        # TEXTS
        locale = appbuilder.get_primary_locale(meta_app)
                
        for text_type, definition in self.active_theme.user_content['texts'].items():

            text_initial = None

            # try to fetch field content from db
            if locale and text_type in locale:
                text_initial = locale[text_type]

            help_text = definition.get('help_text', None)
            if help_text:
                help_text = _(help_text)

            text_required = definition.get('required', False)
            
            self.fields[text_type] = forms.CharField(widget=forms.Textarea, help_text=help_text,
                                                     required=text_required, initial=text_initial)

            self.localizeable_fields.append(text_type)
            

        self.fields['input_language'].initial = self.language

        for field_name in self.localizeable_fields:
            self.fields[field_name].language = self.language

        for field_name, field in self.legal_notice_fields.items():
            field.is_legal_notice_field = True
            
            if field_name == 'entity_name':
                field.is_legal_notice_first = True
            else:
                field.is_legal_notice_first = False
            self.fields[field_name] = field


'''
    AppThemeImageForm
    - App Theme Images do not offer the cropping of images
    - restrictions are loaded from the theme
'''
from localcosmos_server.validators import FileExtensionValidator, ImageRatioValidator, ImageDimensionsValidator
from localcosmos_server.fields import SVGandImageField

VALIDATOR_CLASS_MAP = {
    'file_type' : FileExtensionValidator,
    'ratio' : ImageRatioValidator,
    'dimensions' : ImageDimensionsValidator,
}

class AppThemeImageForm(ManageContentImageFormCommon, LicencingFormMixin):

    # image_type
    image_type = forms.CharField(widget=forms.HiddenInput)

    # md5
    md5 = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, meta_app, *args, **kwargs):
        self.meta_app = meta_app
        self.active_theme = self.meta_app.get_theme()
        super().__init__(*args, **kwargs)

    def get_source_image_field(self):
        # image_type HAS TO be in initial or data for AppThemeImages
        if 'image_type' in self.data:
            image_type = self.data['image_type']
        else:
            image_type = self.initial['image_type']

        # read help_text and validators from theme config
        image_definition = self.active_theme.user_content['images'][image_type]

        help_text = image_definition.get('help_text', None)
        if help_text:
            help_text = _(help_text)

        validators = []
        for restriction_type, restriction in image_definition['restrictions'].items():
            ValidatorClass = VALIDATOR_CLASS_MAP[restriction_type]
            validator = ValidatorClass(restriction)
            validators.append(validator)
        
        source_image_field = SVGandImageField(widget=ImageInputWithPreview, help_text=help_text, required=False,
                                              validators=validators)
        
        source_image_field.widget.current_image = self.current_image

        return source_image_field


    # the form has to be invalid if no image exists and the user uploads only a licence
    def clean(self):
        cleaned_data = super().clean()
        file_ = cleaned_data.get('source_image')

        if not file_:
            image_type = cleaned_data['image_type']
            app_theme_image = AppThemeImage(self.meta_app, image_type)
            if not app_theme_image.exists():
                raise forms.ValidationError(_('You have to upload an image.'))
        return cleaned_data


class TranslateAppForm(forms.Form):

    page_size = 30

    def __init__(self, meta_app, *args, **kwargs):
        self.meta_app = meta_app

        self.page = kwargs.pop('page', 1)
        
        super().__init__(*args, **kwargs)

        appbuilder = meta_app.get_preview_builder()
        
        primary_locale = appbuilder.get_primary_locale(meta_app)
        all_items = list(primary_locale.items())
        all_items_count = len(all_items)

        self.total_pages = math.ceil(all_items_count / self.page_size)
        self.pages = range(1, self.total_pages+1)
        
        start = ((self.page-1) * self.page_size)
        end = self.page * self.page_size
        if end > all_items_count:
            end = all_items_count

        page_items = list(primary_locale.items())[start:end]

        for key, value in page_items:

            languages = meta_app.secondary_languages()

            translation_complete = True

            fieldset = []

            for counter, language in enumerate(languages, 1):

                to_locale = appbuilder.get_locale(self.meta_app, language)
                if not to_locale:
                    to_locale = {}

                # b64 encode the source key to make it a valid html field name attribute
                field_name_utf8 = '{0}-{1}'.format(language, key)

                field_name = base64.b64encode(field_name_utf8.encode()).decode()

                initial = to_locale.get(key, None)
                if initial == None:
                    translation_complete = False
                    
                widget = forms.TextInput

                if len(value) > 50:
                    widget = forms.Textarea            
            
                field = forms.CharField(widget=widget, label=value, initial=initial, required=False)
                field.language = language
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
        
        for b64_key, value in self.cleaned_data.items():

            if len(value) > 0:
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

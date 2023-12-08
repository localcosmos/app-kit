from django import forms
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

from django.utils.translation import gettext_lazy as _

from app_kit.appbuilder import AppBuilder

from app_kit.utils import unCamelCase

from localcosmos_server.widgets import TwoStepFileInput


'''
    mandatory: legal notice
'''
class FrontendSettingsForm(forms.Form):

    support_email = forms.EmailField(required=False)
    legal_notice = forms.CharField(max_length=4000, widget=forms.Textarea, required=False)
    privacy_policy = forms.CharField(max_length=10000, widget=forms.Textarea, required=False)

    def __init__(self, meta_app, frontend, *args, **kwargs):

        self.layoutable_full_fields = ['legal_notice', 'privacy_policy']
        self.layoutable_simple_fields = []

        self.meta_app = meta_app
        self.frontend = frontend
        app_builder = AppBuilder(meta_app)
        self.frontend_settings = app_builder._get_frontend_settings()
        super().__init__(*args, **kwargs)

        self.get_frontend_settings_fields()

    # read settings['user_content']['images'] and settings['texts']
    def get_frontend_settings_fields(self):

        frontend_content_type = ContentType.objects.get_for_model(self.frontend)

        field_order = []

        if 'images' in self.frontend_settings['userContent']:

            for image_type, image_definition in self.frontend_settings['userContent']['images'].items():

                field_label = unCamelCase(image_type)

                # frontend.image uses namespaced image_type
                content_image = self.frontend.image(image_type)

                # required for container
                content_image_type = self.frontend.get_namespaced_image_type(image_type)

                #delete_url = None
                #if content_image:
                #    delete_url = reverse('delete_content_image', kwargs={'pk':content_image.pk})

                widget_attrs = {
                    'data-url' : 'data_url',
                    'accept' : 'image/*',
                }

                url_kwargs = {
                    'meta_app_id' : self.meta_app.id,
                    'content_type_id' : frontend_content_type.id,
                    'object_id' : self.frontend.id,
                    'image_type' : content_image_type 
                }
                url = reverse('manage_content_image', kwargs=url_kwargs)

                widget_kwargs = {
                    'url' : url,
                    'instance' : content_image,
                    #'delete_url' : delete_url,
                    'image_container_id' : 'content_image_{0}_{1}_{2}'.format(frontend_content_type.id, self.frontend.id,
                                                                                content_image_type)
                }

                help_text = ''

                if 'restrictions' in image_definition:

                    restrictions = image_definition['restrictions']

                    for restriction_type, restriction in restrictions.items():
                        restriction_name = unCamelCase(restriction_type)

                        if isinstance(restriction, str):
                            restriction_text = restriction
                        else:
                            restriction_text = ' '.join(restriction)

                        if len(help_text) > 0:
                            help_text = '{0}, '.format(help_text)

                        help_text = '{0}{1}: {2}'.format(help_text, restriction_name, restriction_text)

                    
                    pythonic_restrictions = self.frontend.get_content_image_restrictions(content_image_type)
                    #print(pythonic_restrictions)
                    widget_kwargs['restrictions'] = pythonic_restrictions


                field_kwargs = {
                    'label' : field_label,
                    'help_text' : help_text,
                    'required' : False,
                }

                image_field = forms.ImageField(widget=TwoStepFileInput(widget_attrs, **widget_kwargs), **field_kwargs)

                self.fields[image_type] = image_field

                field_order.append(image_type)

            field_order.append('support_email')
            field_order.append('legal_notice')
            field_order.append('privacy_policy')
            self.order_fields(field_order)

        
        if 'texts' in self.frontend_settings['userContent']:

            for text_type, text_definition in self.frontend_settings['userContent']['texts'].items():

                label = unCamelCase(text_type)

                required = text_definition.get('required', False)

                help_text = text_definition.get('helpText', '')

                field = forms.CharField(label=label, required=required, widget=forms.Textarea, help_text=help_text)

                self.fields[text_type] = field

                if text_type not in self.layoutable_full_fields:

                    self.layoutable_full_fields.append(text_type)


        if 'configuration' in self.frontend_settings['userContent']:

            for configuration_type, configuration_definition in self.frontend_settings['userContent']['configuration'].items():

                label = unCamelCase(configuration_type)

                required = configuration_definition.get('required', False)

                help_text = configuration_definition.get('helpText', '')

                field = forms.CharField(label=label, required=required, widget=forms.TextInput, help_text=help_text)

                self.fields[configuration_type] = field



class ChangeFrontendForm(forms.Form):

    def __init__(self, meta_app, *args, **kwargs):
        self.meta_app = meta_app
        super().__init__(*args, **kwargs)

        self.fields['frontend_name'] = forms.ChoiceField(choices=self.get_frontend_choices(),
            widget=forms.Select, label=_('Frontend'))


    def get_frontend_choices(self):

        preview_builder = self.meta_app.get_preview_builder()

        installed_frontends = preview_builder.get_installed_frontends()

        choices = []

        for frontend_name in installed_frontends:
            choices.append((frontend_name, frontend_name))
        
        return choices
    

from django.core.validators import FileExtensionValidator
class UploadPrivateFrontendForm(forms.Form):
    frontend_zip = forms.FileField(validators=[FileExtensionValidator(allowed_extensions=['zip'])])


class InstallPrivateFrontendForm(forms.Form):
    frontend_name = forms.CharField(widget=forms.HiddenInput)
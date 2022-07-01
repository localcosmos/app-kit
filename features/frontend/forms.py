from django import forms
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

from app_kit.appbuilder import AppBuilder

from localcosmos_server.widgets import TwoStepFileInput


'''
    mandatory: legal notice
'''
class FrontendSettingsForm(forms.Form):

    legal_notice = forms.CharField(max_length=355, widget=forms.Textarea, required=False)

    layoutable_full_fields = ['legal_notice']

    def __init__(self, meta_app, frontend, *args, **kwargs):
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

        if 'images' in self.frontend_settings['user_content']:

            for image_type, image_definition in self.frontend_settings['user_content']['images'].items():

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

                    widget_kwargs['restrictions'] = restrictions

                    for restriction_type, restriction in restrictions.items():
                        restriction_name = ' '.join(restriction_type.split('_')).capitalize()

                        if isinstance(restriction, str):
                            restriction_text = restriction
                        else:
                            restriction_text = ' '.join(restriction)

                        if len(help_text) > 0:
                            help_text = '{0}, '.format(help_text)

                        help_text = '{0}{1}:{2}'.format(help_text, restriction_name, restriction_text)


                field_kwargs = {
                    'help_text' : help_text,
                    'required' : False,
                }

                image_field = forms.ImageField(widget=TwoStepFileInput(widget_attrs, **widget_kwargs), **field_kwargs)

                self.fields[image_type] = image_field

                field_order.append(image_type)

            field_order.append('legal_notice')
            self.order_fields(field_order)

        
        if 'texts' in self.frontend_settings['user_content']:

            for text_type, text_definition in self.frontend_settings['user_content']['texts'].items():

                label = ' '.join(text_type.split('_')).capitalize()

                required = text_definition.get('required', False)

                help_text = text_definition.get('help_text', '')

                field = forms.CharField(label=label, required=required, widget=forms.Textarea, help_text=help_text)

                self.fields[text_type] = field

                if text_type not in self.layoutable_full_fields:

                    self.layoutable_full_fields.append(text_type)

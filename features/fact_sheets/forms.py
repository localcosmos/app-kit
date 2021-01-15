from django.conf import settings
from django import forms
from django.utils.translation import gettext_lazy as _

from django.core.validators import FileExtensionValidator

from .models import FactSheetTemplates, FactSheetImages, build_factsheets_templates_upload_path

from .definitions import TEXT_LENGTH_RESTRICTIONS

from localcosmos_server.forms import LocalizeableForm

from .parser import FactSheetTemplateParser

import os


class FactSheetFormCommon(LocalizeableForm):
    title = forms.CharField(label=_('Title'), max_length=TEXT_LENGTH_RESTRICTIONS['FactSheet']['title'])
    navigation_link_name = forms.CharField(label=_('Name for links in navigation menus'),
            max_length=TEXT_LENGTH_RESTRICTIONS['FactSheet']['navigation_link_name'],
            help_text=_('Max %(characters)s characters. If this content shows up in a navigation menu, this name will be shown as the link.') % {'characters' : TEXT_LENGTH_RESTRICTIONS['FactSheet']['navigation_link_name']})

    localizeable_fields = ['title', 'navigation_link_name']



'''
    there 2 types of templates:
    - provided by Local Cosmos
    - uploaded by the user
'''
class CreateFactSheetForm(FactSheetFormCommon):

    template_name = forms.ChoiceField(label=_('Template'))

    def __init__(self, meta_app, fact_sheets, **kwargs):
        self.meta_app = meta_app
        self.fact_sheets = fact_sheets
        super().__init__(**kwargs)

        choices = self.get_template_choices()
        self.fields['template_name'].choices = choices


    def get_template_choices(self):
        templates = self.meta_app.get_fact_sheet_templates()

        # add custom templates
        custom_templates = FactSheetTemplates.objects.filter(fact_sheets=self.fact_sheets)

        for template in custom_templates:
            name = template.name
            if not name:
                name = os.path.basename(template.template.name)
            choice = (template.template.name, name)
            templates.append(choice)
            
        return templates



class ManageFactSheetForm(FactSheetFormCommon):

    def __init__(self, meta_app, fact_sheet, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fact_sheet = fact_sheet

        self.layoutable_full_fields = set([])
        self.layoutable_simple_fields = set([])


        # find all cms template tags in source
        parser = FactSheetTemplateParser(meta_app, fact_sheet)
        cms_tags = parser.parse()

        # the fields should be in self.fields        
        for tag in cms_tags:

            instances = []

            if tag.microcontent_category in ['image', 'images']:
                instances = FactSheetImages.objects.filter(fact_sheet=self.fact_sheet,
                                                           microcontent_type=tag.microcontent_type)

            # get cms form fields for each tag
            for field in tag.form_fields(instances=instances):
                
                self.fields[field['name']] = field['field']

                self.fields[field['name']].language = fact_sheet.fact_sheets.primary_language
                
                if 'layoutable-simple' in tag.args:
                    self.layoutable_simple_fields.add(field['name'])
                elif 'layoutable-full' in tag.args:
                    self.layoutable_full_fields.add(field['name'])
   


from content_licencing.mixins import LicencingFormMixin
from localcosmos_server.widgets import ImageInputWithPreview
from localcosmos_server.forms import ManageContentImageFormCommon
class UploadFactSheetImageForm(ManageContentImageFormCommon, LicencingFormMixin, forms.Form):

    def get_source_image_field(self):
        # unfortunately, a file field cannot be prepoluated due to html5 restrictions
        # therefore, source_image has to be optional. Otherwise, editing would be impossible
        # check if a new file is required in clean
        required = False
        image_file = None
        
        if self.current_image:
            image_file = self.current_image.image
        else:
            required = True
        source_image_field = forms.ImageField(widget=ImageInputWithPreview, required=required)
        source_image_field.widget.current_image = image_file

        return source_image_field


# check if the template already exists in templates provided by the theme
class UploadFactSheetTemplateForm(forms.Form):

    template = forms.FileField(validators=[FileExtensionValidator(allowed_extensions=['html'])])
    name = forms.CharField(required=False)
    overwrite_existing_template = forms.BooleanField(required=False)

    def __init__(self, fact_sheets, *args, **kwargs):
        self.fact_sheets = fact_sheets
        super().__init__(*args, **kwargs)

    def clean(self):

        template = self.cleaned_data.get('template')

        if template:
            overwrite = self.cleaned_data.get('overwrite_existing_template', False)

            path = build_factsheets_templates_upload_path(self.fact_sheets, template.name)

            exists = FactSheetTemplates.objects.filter(fact_sheets=self.fact_sheets,
                                                       template=path).exists()

            
            if exists and not overwrite:
                del self.cleaned_data['template']
                raise forms.ValidationError(
                    _('This template already exists. Did you want to overwrite the existing one?'))
        
        return self.cleaned_data

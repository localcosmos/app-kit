from django.conf import settings
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import FactSheetTemplates

from .definitions import TEXT_LENGTH_RESTRICTIONS

from localcosmos_server.forms import LocalizeableForm

from .parser import FactSheetTemplateParser


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

    def __init__(self, meta_app, **kwargs):
        self.meta_app = meta_app
        super().__init__(**kwargs)

        choices = self.get_template_choices()
        self.fields['template_name'].choices = choices


    def get_template_choices(self):
        templates = self.meta_app.get_fact_sheet_templates()
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

            # get cms form fields for each tag
            for field in tag.form_fields():
                
                self.fields[field['name']] = field['field']

                self.fields[field['name']].language = fact_sheet.fact_sheets.primary_language
                
                if 'layoutable-simple' in tag.args:
                    self.layoutable_simple_fields.add(field['name'])
                elif 'layoutable-full' in tag.args:
                    self.layoutable_full_fields.add(field['name'])

        

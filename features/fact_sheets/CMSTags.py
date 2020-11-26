from django import forms
from django.conf import settings

from django.utils.translation import gettext as _

import os, json


"""
    CMSTag is an object created from a template tag
"""
class CMSTag:

    def __init__(self, fact_sheet, microcontent_category, microcontent_type, *args, **kwargs):

        self.fact_sheet = fact_sheet
        
        self.microcontent_category = microcontent_category
        self.microcontent_type = microcontent_type
        self.args = list(args)

        self.multi = False
        self.min_num = kwargs.get('min', 0)
        self.max_num = kwargs.get('max', None)

        
        if 'multi' in args:
            self.multi = True
            
        elif self.microcontent_category in ['images', 'microcontents']:
            self.multi = True
            self.args.append('multi')



    def _get_widget_attrs(self):
        widget_attrs = {
            'data-microcontentcategory' : self.microcontent_category,
            'data-microcontenttype' : self.microcontent_type,
            'data-type' : '{0}-{1}'.format(self.microcontent_category, self.microcontent_type),
        }

        return widget_attrs

    '''
    return the form fields
    '''
    def form_fields(self):

        form_fields = []

        widget_attrs = self._get_widget_attrs()

        if self.multi:
            pass

        # non-multi fields
        else:

            if self.microcontent_category in ['image', 'images']:
                pass

            else:
                widget = forms.Textarea
                if 'short' in self.args:
                    widget = forms.TextInput

                initial = ''

                if self.fact_sheet.contents and self.microcontent_category in self.fact_sheet.contents:
                    initial = fact_sheet.contents[self.microcontent_category]

                label = self.microcontent_type.replace('_', ' ').capitalize()
                                                  
                field_kwargs = {
                    'widget' : widget,
                    'initial' : initial,
                    'required' : False,
                    'label' : label,
                }
                                                  
                form_field = forms.CharField(**field_kwargs)

                field = {
                    'name' : self.microcontent_type,
                    'field' : form_field,
                }
                
                form_fields.append(field)

        return form_fields       

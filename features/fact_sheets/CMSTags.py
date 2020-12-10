from django import forms
from django.conf import settings
from django.urls import reverse

from django.utils.translation import gettext as _

from localcosmos_server.online_content.fields import MultiContentField
from localcosmos_server.online_content.widgets import MultiContentWidget

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
        self.is_file = False
        self.min_num = kwargs.get('min', 0)
        self.max_num = kwargs.get('max', None)

        if self.microcontent_category in ['image', 'images']:
            self.is_file = True
        
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

        if self.multi:
            widget_attrs.update({
                'multi' : True,
            })

        return widget_attrs


    def get_label(self):
        return self.microcontent_type.replace('_', ' ').capitalize()


    def get_image_form_field(self, current_image=None):

        widget_attrs = self._get_widget_attrs()

        label = self.get_label()

        field_kwargs = {
            'required' : False,
            'label' : label
        }
        
        delete_url = None

        data_url_kwargs = {
            'fact_sheet_id' : self.fact_sheet.id,
            'microcontent_category' : self.microcontent_category,
            'microcontent_type' : self.microcontent_type,
        }

        data_url = reverse('upload_factsheet_image', kwargs=data_url_kwargs)

        if current_image:

            data_url_kwargs['pk'] = current_image.pk
            data_url = reverse('manage_factsheet_image', kwargs=data_url_kwargs)
            
            delete_kwargs = {
                'pk' : current_image.pk,
            }
            delete_url = reverse('delete_factsheet_image', kwargs=delete_kwargs)
            delete_url = '{0}?microcontent_category={1}'.format(delete_url, self.microcontent_category)
            
        widget_attrs['data-url'] = data_url  
        widget_attrs['accept'] = 'image/*'

        form_field = forms.ImageField(widget=forms.FileInput(widget_attrs), **field_kwargs)
        form_field.cms_tag = self
        form_field.current_image = current_image

        form_field.licenced_url = data_url
        form_field.delete_url = delete_url

        return form_field

        
    '''
    return the form fields
    '''
    def form_fields(self, instances=[]):

        form_fields = []

        if self.microcontent_category in ['image', 'images']:

            if self.multi:

                is_first = True
                is_last = False
                field_count = 0

                for current_image in instances:

                    field_count += 1

                    form_field = self.get_image_form_field(current_image)

                    if field_count == self.max_num:
                        is_last = True

                    form_field.is_first = is_first
                    form_field.is_last = is_last
                    
                    field_name = '{0}-{1}'.format(self.microcontent_type, field_count)

                    field = {
                        'name' : field_name,
                        'field' : form_field,
                    }

                    form_fields.append(field)

                    if is_first == True:
                        is_first = False


                # optionally add empty field
                if self.max_num is None or field_count < self.max_num:
                    # is_last is False
                    is_last = True

                    form_field = self.get_image_form_field()
                    
                    form_field.is_first = is_first
                    form_field.is_last = is_last
            
                    field = {
                        'name' : self.microcontent_type,
                        'field' : form_field,
                    }
                    
                    form_fields.append(field)
                    

            else:

                current_image = None

                if instances:
                    current_image = instances[0]
                
                form_field = self.get_image_form_field(current_image)

                field = {
                    'name' : self.microcontent_type,
                    'field' : form_field,
                }
                
                form_fields.append(field)
        
        else:

            widget_attrs = self._get_widget_attrs()

            label = self.get_label()

            field_kwargs = {
                'required' : False,
                'label' : label
            }

            if self.multi:

                pass

                '''

                field_kwargs.update({
                    'widget' : MultiContentWidget(widget_attrs),
                })

                if self.fact_sheet.contents and self.microcontent_category in self.fact_sheet.contents:

                    contents = fact_sheet.contents
                    field_count = 0

                    if isinstance(contents, list):

                        is_first = True
                        is_last = False

                        for content in contents:

                            field_count += 1

                            field_name = '{0}-{1}'.format(self.microcontent_type, field_count)

                            field_kwargs = {
                                'initial' : content,
                            }

                            form_field = forms.CharField(**field_kwargs)
                            form_field.cms_tag = self

                            field = {
                                'name' : self.microcontent_type,
                                'field' : form_field,
                            }
                            form_fields.append(field)

                            is_first = False

                            if self.max_num is None or self.max_num <= field_count:
                                # check if this is the last field
                                if self.max_num is not None and field_count == self.max_num:
                                    is_last = True
                                    break
                                
                # optionally add empty field
                if self.max_num is None or field_count < self.max_num:
                    # is_last is False
                    is_last = True

                    form_field = forms.CharField(**field_kwargs)
                    form_field.cms_tag = self
            
                    field = {
                        'name' : self.microcontent_type,
                        'field' : form_field,
                    }
                    
                    form_fields.append(field)
                    is_first = False
                '''

                            
            # non-multi fields
            else:

                widget = forms.Textarea
                if 'short' in self.args:
                    widget = forms.TextInput

                initial = ''

                if self.fact_sheet.contents and self.microcontent_category in self.fact_sheet.contents:
                    initial = fact_sheet.contents[self.microcontent_category]
                                                  
                field_kwargs.update({
                    'widget' : widget,
                    'initial' : initial,
                })
                                                  
                form_field = forms.CharField(**field_kwargs)
                form_field.cms_tag = self

                field = {
                    'name' : self.microcontent_type,
                    'field' : form_field,
                }
                
                form_fields.append(field)

        return form_fields       

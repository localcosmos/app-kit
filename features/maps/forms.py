from django import forms
from app_kit.forms import GenericContentOptionsForm
from django.utils.translation import gettext_lazy as _

import json

class MapsOptionsForm(GenericContentOptionsForm):

    initial_latitude = forms.FloatField(widget=forms.NumberInput(attrs={"readonly":True}), required=False)
    initial_longitude = forms.FloatField(widget=forms.NumberInput(attrs={"readonly":True}), required=False)
    initial_zoom = forms.IntegerField(widget=forms.NumberInput(attrs={"readonly":True}), required=False)


class ProjectAreaForm(forms.Form):

    area = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_area(self):

        geojson_str = self.cleaned_data['area']

        if len(geojson_str) > 0:

            try:
                geojson = json.loads(geojson_str)
            except:
                del self.cleaned_data['area']
                raise forms.ValidationError(_('Invalid geometry'))
        
        return geojson_str

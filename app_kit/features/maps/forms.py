from django import forms
from app_kit.forms import GenericContentOptionsForm
from django.utils.translation import gettext_lazy as _

from localcosmos_server.forms import LocalizeableForm

from localcosmos_server.taxonomy.fields import TaxonField

from app_kit.utils import get_appkit_taxon_search_url

from .models import FilterTaxon

import json

class MapsOptionsForm(GenericContentOptionsForm):

    initial_latitude = forms.FloatField(widget=forms.NumberInput(attrs={"readonly":True}), required=False)
    initial_longitude = forms.FloatField(widget=forms.NumberInput(attrs={"readonly":True}), required=False)
    initial_zoom = forms.IntegerField(widget=forms.NumberInput(attrs={"readonly":True}), required=False)

    include_observation_forms_as_filters = forms.BooleanField(required=False)


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



class TaxonomicFilterForm(LocalizeableForm):

    def __init__(self, *args, **kwargs):
        self.taxonomic_filter = kwargs.pop('taxonomic_filter', None)
        super().__init__(*args, **kwargs)

    name = forms.CharField(max_length=355)

    taxon = TaxonField(label=_('Add taxon'),
                    taxon_search_url=get_appkit_taxon_search_url, required=False)

    localizeable_fields = ['name']

    def clean_taxon(self):

        taxon = self.cleaned_data.get('taxon', None)

        if taxon and self.taxonomic_filter:
            taxon_exists = FilterTaxon.objects.filter(taxonomic_filter=self.taxonomic_filter,
                name_uuid=taxon.name_uuid).exists()

            if taxon_exists:
                del self.cleaned_data['taxon']
                raise forms.ValidationError(_('Taxon already exists'))

            # check if taxon is a subtaxon of an existing filter taxon
            for existing_taxon in self.taxonomic_filter.taxa:

                if existing_taxon.taxon_source == taxon.taxon_source and taxon.taxon_nuid.startswith(existing_taxon.taxon_nuid):
                    del self.cleaned_data['taxon']
                    raise forms.ValidationError(_('%(taxon_name)s is a subtaxon of %(existing_taxon_name)s') % {
                        'taxon_name' : taxon.taxon_latname,
                        'existing_taxon_name': existing_taxon.taxon_latname,
                    })

        return taxon

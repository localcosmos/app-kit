from django import forms
from django.utils.translation import gettext_lazy as _
from localcosmos_server.forms import LocalizeableForm

from .models import MetaVernacularNames

class ManageMetaVernacularNameForm(LocalizeableForm):
    
    name = forms.CharField()

    preferred = forms.BooleanField(help_text=_('This name is the preferred name of this species'), required=False)
    
    localizeable_fields = ['name',]
    
    def __init__(self, lazy_taxon, meta_vernacular_name=None, *args, **kwargs):
        self.lazy_taxon = lazy_taxon
        self.meta_vernacular_name = meta_vernacular_name
        super().__init__(*args, **kwargs)
    
    
    def clean_name(self):
        name = self.cleaned_data['name']
        name = name.strip()
        return name
    
    def clean(self):
        name = self.cleaned_data.get('name', None)
        language = self.cleaned_data.get('input_language', None)
        
        if name and language:
            existing_name = MetaVernacularNames.objects.filter(
                taxon_source=self.lazy_taxon.taxon_source,
                name_uuid=self.lazy_taxon.name_uuid,
                name=name,
                language=language,
            ).first()
            
            if existing_name:
                error_message = _('This name already exists')
                if not self.meta_vernacular_name:
                    self.add_error('name', error_message)
                elif self.meta_vernacular_name and existing_name.pk != self.meta_vernacular_name.pk:
                    self.add_error('name', error_message)
        
        return self.cleaned_data
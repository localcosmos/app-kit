from django import forms

from .models import GlossaryEntry

from django.utils.translation import gettext_lazy as _

from localcosmos_server.forms import LocalizeableModelForm

from app_kit.forms import GenericContentOptionsForm

class GlossaryOptionsForm(GenericContentOptionsForm):
    
    version = forms.CharField(help_text=_('You can manually set you own version here. This will not affect the automated versioning.'), required=False)
    

class GlossaryEntryForm(LocalizeableModelForm):

    localizeable_fields = ('term', 'synonyms', 'definition',)

    synonyms = forms.CharField(max_length=255, required=False,
                               help_text=_('Words that should also link to this glossary entry. Separate with commas.'))

    field_order = ['glossary', 'term', 'synonyms', 'definition']

    class Meta:
        model = GlossaryEntry
        fields = ('__all__')

        widgets = {
            'glossary' : forms.HiddenInput,
        }



from app_kit.forms import OptionalContentImageForm
class GlossaryEntryWithImageForm(OptionalContentImageForm, GlossaryEntryForm):

    localizeable_fields = ('term', 'synonyms', 'definition',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        field_order = [
            'glossary',
            'term',
            'synonyms',
            'definition',
            'source_image',
            'image_type',
            'crop_parameters',
            'features',
            'md5',
            'creator_name',
            'creator_link',
            'source_link',
            'licence',
            'requires_translation',
        ]

        self.order_fields(field_order)

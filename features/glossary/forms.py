from django import forms

from .models import GlossaryEntry

from django.utils.translation import gettext_lazy as _

from localcosmos_server.forms import LocalizeableModelForm

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

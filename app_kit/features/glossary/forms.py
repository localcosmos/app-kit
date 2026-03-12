from django import forms

from .models import GlossaryEntry, GlossaryEntryCategory

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


class GlossaryEntryCategoryForm(forms.ModelForm):
    
    def __init__(self, glossary, *args, **kwargs):
        self.glossary = glossary
        super().__init__(*args, **kwargs)
    
    def clean_name(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name', None)

        if self.instance.pk:
            existing_categories = GlossaryEntryCategory.objects.filter(glossary=self.instance.glossary).exclude(pk=self.instance.pk)
        else:
            existing_categories = GlossaryEntryCategory.objects.filter(glossary=self.glossary)

        if existing_categories.filter(name=name).exists():
            raise forms.ValidationError(_('A category with this name already exists in this glossary. Please choose a different name.'))

        return name

    class Meta:
        model = GlossaryEntryCategory
        exclude = ('glossary',)
        labels = {
            'name' : _('Category name'),
        }
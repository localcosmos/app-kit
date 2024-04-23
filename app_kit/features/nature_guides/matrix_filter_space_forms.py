# forms for spaces of matrix filters
from django.utils.translation import gettext_lazy as _

from django import forms

from localcosmos_server.forms import LocalizeableForm

from .definitions import TEXT_LENGTH_RESTRICTIONS

from app_kit.validators import json_compatible

class MatrixFilterSpaceForm(LocalizeableForm):

    # edit space id id is given
    matrix_filter_space_id = forms.IntegerField(widget=forms.HiddenInput, required=False)

    layoutable_simple_fields = []

    def save(self, form):
        raise NotImplementedError('MatrixFilterSpaceForm subclasses need a save method')
    

'''
    Images are separate forms in LocalCosmos
'''
from app_kit.forms import OptionalContentImageForm
class DescriptiveTextAndImagesFilterSpaceForm(OptionalContentImageForm, MatrixFilterSpaceForm):

    text = forms.CharField(label=_('Text'), widget=forms.Textarea,
        max_length=TEXT_LENGTH_RESTRICTIONS['DescriptiveTextAndImages']['description'], validators=[json_compatible])
    
    localizeable_fields = ['text']
    layoutable_simple_fields = ['text']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.move_to_end('text', last=False)


class TextOnlyFilterSpaceForm(MatrixFilterSpaceForm):

    text = forms.CharField(label=_('Text'), widget=forms.Textarea,
        max_length=TEXT_LENGTH_RESTRICTIONS['TextOnlyFilter']['text'], validators=[json_compatible])
    
    localizeable_fields = ['text']

    layoutable_simple_fields = ['text']


'''
    define/change an rgb color
'''
COLOR_TYPES = (
    ('single', _('single color')),
    ('gradient', _('gradient')),
    ('triplet', _('triplet')),
)
class ColorFilterSpaceForm(MatrixFilterSpaceForm):

    localizeable_fields = []

    color_type = forms.ChoiceField(label=_('Color type'), choices=COLOR_TYPES)

    color = forms.CharField(widget=forms.TextInput(attrs={'type':'color'}))

    color_2 = forms.CharField(required=False, widget=forms.TextInput(attrs={'type':'color'}))

    color_3 = forms.CharField(required=False, widget=forms.TextInput(attrs={'type':'color'}))
    
    description = forms.CharField(max_length=TEXT_LENGTH_RESTRICTIONS['ColorFilter']['description'],
                                  required=False)

    def clean(self):
        
        cleaned_data = super().clean()

        gradient = cleaned_data.get('gradient', False)
        color_2 = cleaned_data.get('color_2', None)

        if gradient and not color_2:
            self.add_error('color_2', _('You have to define a second color if you want to create a gradient.'))

        return cleaned_data

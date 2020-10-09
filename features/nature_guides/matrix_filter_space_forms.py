# forms for spaces of matrix filters
from django.utils.translation import gettext_lazy as _

from django import forms

from localcosmos_server.forms import LocalizeableForm

from .definitions import TEXT_LENGTH_RESTRICTIONS

class MatrixFilterSpaceForm(LocalizeableForm):

    # edit space id id is given
    matrix_filter_space_id = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def save(self, form):
        raise NotImplementedError('MatrixFilterSpaceForm subclasses need a save method')
    

'''
    Images are separate forms in LocalCosmos
'''
from app_kit.forms import OptionalContentImageForm
class DescriptiveTextAndImagesFilterSpaceForm(OptionalContentImageForm, MatrixFilterSpaceForm):

    text = forms.CharField(label=_('Text'), max_length=TEXT_LENGTH_RESTRICTIONS['DescriptiveTextAndImages']['name'])
    
    localizeable_fields = ['text']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.move_to_end('text', last=False)


class TextOnlyFilterSpaceForm(MatrixFilterSpaceForm):

    text = forms.CharField(label=_('Text'), widget=forms.Textarea,
                           max_length=TEXT_LENGTH_RESTRICTIONS['TextOnlyFilter']['text'])
    
    localizeable_fields = ['text']


'''
    define/change an rgb color
'''
class ColorFilterSpaceForm(MatrixFilterSpaceForm):

    localizeable_fields = []

    color = forms.CharField(widget=forms.TextInput(attrs={'type':'color'}))

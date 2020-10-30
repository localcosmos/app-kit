from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .widgets import DefineRangeSpaceWidget

'''
    If a user adds/manages a Node which is attached to a matrix he has to define the trait space for this node

    We need form fields that offer user friendly input and produce valid encoded spaces from that input

    A) a field/widget for creating a free space, eg when adding a node to a matrix
    B) a field/widget for actually using the matrix key, which might use the trait's definition plus its space
        - creating a subspace of the matrix space

    Both return an encoded space, so the field should be the same, the widget may differ

    A) -> 'DEFINE'SpaceWidget (eg for Range: a min value and a max value)
    B) -> 'SELECT'SpaceWidget (eg for Range: a slider with one or two slideable dots)

'''    

class RangeSpaceField(forms.MultiValueField):

    widget = DefineRangeSpaceWidget

    def __init__(self, *args, **kwargs):

        subfield_kwargs = kwargs.pop('subfield_kwargs', {})
        
        fields = (
            forms.DecimalField(**subfield_kwargs), # min
            forms.DecimalField(**subfield_kwargs), # max
        )
        super().__init__(fields, *args, **kwargs)



    def clean(self, value):
        # value is a list of unicode
        
        if value and len(value) > 0:
            if len(value) == 1:
                raise forms.ValidationError(_('Both min and max value are required.'))

            else:
                
                if not value[0] and not value[1]:
                    return None
                if not value[0] or not value[1]:
                    raise forms.ValidationError(_('Both min and max value are required.'))

                value_0 = float(value[0])
                value_1 = float(value[1])

                if not value_0 <= value_1:
                    raise forms.ValidationError(_('Min needs to be smaller than max,'))

        return super().clean(value)


    # create a valid encoded_space
    # compress received valid data_list
    def compress(self, data_list):
        # data_list: [min, max]
        if data_list and len(data_list) == 2:

            return [float(i) for i in data_list]

        return None


class ObjectLabelModelChoiceIterator(forms.models.ModelChoiceIterator):
    
    def choice(self, obj):
        choice_extra_kwargs = {
            'instance' : obj,
        }
        return (self.field.prepare_value(obj), obj)
    

class ObjectLabelModelMultipleChoiceField(forms.ModelMultipleChoiceField):

    iterator = ObjectLabelModelChoiceIterator

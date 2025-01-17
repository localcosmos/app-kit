from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.contrib.gis import forms
from django.urls import reverse
from django.utils import timezone
from datetime import datetime

from .models import (GenericForm, DJANGO_FIELD_WIDGETS, NUMBER_FIELDS, FIELD_OPTIONS,
    NON_DJANGO_FIELD_OPTIONS)

from . import fields, widgets
from .definitions import TEXT_LENGTH_RESTRICTIONS

from localcosmos_server.forms import LocalizeableForm
from localcosmos_server.taxonomy.widgets import (get_choices_from_taxonomic_restrictions,
                                                 get_taxon_map_from_taxonomic_restrictions)

class DynamicForm(forms.Form):
    
    def __init__(self, dynamic_fields, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # generic fields are added as uuid, baseform fields just normal
        for dynamic_field in dynamic_fields:
            self.fields[str(dynamic_field.uuid)] = dynamic_field.django_field


# build a django form field from the database
class DynamicField:

    # receives field as dictionary
    def __init__(self, generic_field_link, language, meta_app):

        generic_field = generic_field_link.generic_field

        self.uuid = str(generic_field.uuid)

        try:
            django_field = getattr(fields, generic_field.field_class)
        except:
            django_field = getattr(forms, generic_field.field_class) 
        try:
            widget = getattr(forms, generic_field.render_as)
        except:
            widget = getattr(widgets, generic_field.render_as)
            
        label = generic_field.label


        widget_attrs = {}
        widget_kwargs = {}

        initparams = {
            'label' : label,
            'required' : generic_field_link.is_required,
            'help_text' : generic_field.help_text,
        }

        # create initparams, later django_field(**init_params)
        if generic_field.field_class in ['ChoiceField', 'MultipleChoiceField']:
            
            choices = []

            if generic_field.field_class == 'ChoiceField' and generic_field_link.is_required == False:
                choices.append(('','-------'))
            
            initial = None
            
            for generic_value in generic_field.choices():
                                
                choices.append(
                    (generic_value.text_value, generic_value.name)
                )

                if generic_value.is_default == True:
                    initial = generic_value.text_value

            initparams.update({
                'choices' : choices,
                'initial' : initial,
            })
            
        elif generic_field.field_class in ['DecimalField', 'FloatField', 'IntegerField']:

            initial = None

            min_value = generic_field.get_option('min_value')
            if min_value:
                initial = min_value

            initparams.update({
                'initial' : initial,
            })

            step = generic_field.get_option('step')
            if step:
                widget_attrs['step'] = step

            unit = generic_field.get_option('unit')
            if unit:
                initparams['label'] = '{0} ({1})'.format(label, unit)

        elif generic_field.field_class == 'TaxonField':

            url_kwargs = {
                'meta_app_id':meta_app.id,
            }

            additional_params = {
                'taxon_search_url' : reverse('search_backbonetaxonomy', kwargs=url_kwargs),
                'fixed_taxon_source' : 'taxonomy.sources.col', # irrelevant for search_backbonetaxonomy
                'display_language_field' : False,
            }
            
            initparams.update(additional_params)
            widget_kwargs.update(additional_params)


        elif generic_field.field_class == 'SelectTaxonField':

            choices = []

            taxonomic_restrictions = generic_field.taxonomic_restrictions.all()

            if taxonomic_restrictions:
                choices = get_choices_from_taxonomic_restrictions(taxonomic_restrictions)

            elif not taxonomic_restrictions:
                choices.append(('', _('Please add taxa using taxonomic restritions')))

            initial = None
            taxon_map = get_taxon_map_from_taxonomic_restrictions(taxonomic_restrictions)

            if generic_field_link.is_required == False:
                choices.insert(0, ('','-------'))

            # initial?
            
            initparams.update({
                'choices' : choices,
                'initial' : initial,
                'taxon_map': taxon_map,
            })

            widget_kwargs.update({
                'choices': choices,
                'taxon_map': taxon_map,
            })

        elif generic_field.field_class == 'DateTimeJSONField':
            datetime_mode = generic_field.get_option('datetime_mode')
            widget_attrs['datetime_mode'] = datetime_mode
            if datetime_mode == 'date':
                widget_attrs['type'] = 'date'
                initial = datetime.now().strftime('%Y-%m-%d')
            else:
                widget_attrs['type'] = 'datetime-local'
                initial = timezone.now()

            initparams.update({
                'initial' : initial,
            })


        widget_kwargs['attrs'] = widget_attrs
        initparams['widget'] = widget(**widget_kwargs)

        # add options to initparams
        if generic_field.options:
            option_types = FIELD_OPTIONS.get(generic_field.field_class, [])
            for option_type in option_types:

                # django does not support step, the built app does
                if option_type not in NON_DJANGO_FIELD_OPTIONS:
                
                    option_value = generic_field.options.get(option_type, None)
                    if option_value is not None:
                        initparams[option_type] = option_value

        dynamic_field = django_field(**initparams)
        self.django_field = dynamic_field

        

DATETIME_MODES = (
    ('date', _('Date')),
    ('datetime-local', _('Date and time')),
)

OPTION_FIELDS = {
    'min_value' : forms.FloatField(required=False),
    'max_value' : forms.FloatField(required=False),
    'unit' : forms.CharField(required=False, max_length=255, help_text=_('abbreviated unit, eg cm or m')),
    'decimal_places' : forms.IntegerField(required=False),
    'step' : forms.FloatField(required=False, help_text=_('Defines the step for the + and - buttons.')),
    'initial': forms.FloatField(label=_('Initial'), required=False, help_text=_('The initial value of this field')),
    'datetime_mode' : forms.ChoiceField(required=False, label=_('Mode'), choices=DATETIME_MODES,
                                      initial='datetime'),
    'quadrant_size' : forms.IntegerField(label=_('Quadrant size in meters'), initial=5, min_value=5),
}

# locale inherited from form
from .models import FIELD_ROLES, ALLOWED_WIDGETS
class GenericFieldForm(LocalizeableForm):

    localizeable_fields = ['label']
    
    generic_field_class = forms.CharField(widget=forms.HiddenInput) # always prefilled
    generic_field_role = forms.ChoiceField(widget=forms.HiddenInput, choices=FIELD_ROLES )
    label = forms.CharField(max_length=TEXT_LENGTH_RESTRICTIONS['GenericField']['label'])
    help_text = forms.CharField(required=False, max_length=TEXT_LENGTH_RESTRICTIONS['GenericField']['help_text'])

    is_required = forms.BooleanField(required=False)

    widget = forms.ChoiceField(help_text=_('A widget defines how the field is displayed to the user.')) # depending on field_class, prefilled, user thinks in widgets, not field_classes

    def __init__(self, *args, **kwargs):


        super().__init__(*args, **kwargs)

        field_class_field = self.fields['generic_field_class']

        if hasattr(field_class_field, 'value') and field_class_field.value is not None:
            generic_field_class = field_class_field.value
            
        elif 'generic_field_class' in self.data:
            generic_field_class = self.data['generic_field_class']
        else:
            generic_field_class = self.initial['generic_field_class']

        widget_choices = []

        for widget_id in ALLOWED_WIDGETS[generic_field_class]:
            for tup in DJANGO_FIELD_WIDGETS:
                if tup[0] == widget_id:
                    widget_choices.append(tup)
        
        self.fields['widget'].choices = widget_choices

        if generic_field_class in FIELD_OPTIONS:
            options = FIELD_OPTIONS[generic_field_class]
            for option in options:
                self.fields[option] = OPTION_FIELDS[option]
                self.fields[option].is_option_field = True


        role = self.initial.get('generic_field_role', 'regular')
        if role in ['temporal_reference', 'geographic_reference']:
            self.initial['is_required'] = True
            self.fields['is_required'].widget.attrs['disabled'] = True
            

    def clean_is_required(self):
        is_required = self.cleaned_data.get('is_required', False)
        generic_field_class = self.cleaned_data.get('generic_field_class', None)

        if generic_field_class:

            if generic_field_class == 'MultipleChoiceField' and is_required != False:
                raise forms.ValidationError(_('A multiple choice field cannot be a required field.'))

        return is_required

    def clean_max_value(self):
        max_value = self.cleaned_data.get('max_value', None)

        if max_value:
            generic_field_class = self.cleaned_data['generic_field_class']

            if generic_field_class not in NUMBER_FIELDS:
                raise forms.ValidationError(_('Max value only applies to number fields.'))

            try:
                float_val = float(max_value)
            except:
                raise forms.ValidationError(_('Max value has to be a number.'))
            
            if generic_field_class == 'IntegerField':
                if not float(max_value) == int(float(max_value)):
                    raise forms.ValidationError(_('Integer fields can only have integer max values.'))

            
        return max_value

    def clean_min_value(self):
        min_value = self.cleaned_data.get('min_value', None)

        if min_value is not None:
            generic_field_class = self.cleaned_data['generic_field_class']

            if generic_field_class not in NUMBER_FIELDS:
                raise forms.ValidationError(_('Min value only applies to number fields.'))

            try:
                float_val = float(min_value)
            except:
                raise forms.ValidationError(_('Max value has to be a number.'))
            
            if generic_field_class == 'IntegerField':
                if not float(min_value) == int(float(min_value)):
                    raise forms.ValidationError(_('Integer fields can only have Integer max values.'))
            
        return min_value


    def clean_decimal_places(self):
        decimal_places = self.cleaned_data.get('decimal_places', None)

        if decimal_places:
            generic_field_class = self.cleaned_data['generic_field_class']
            if generic_field_class == 'DecimalField':
                try:
                    decimal_places = int(decimal_places)
                except:
                    raise forms.ValidationError(_('Only integers are accepted.'))
            else:
                raise forms.ValidationError(_('Decimal places can only be used in decimal fields.'))

        return decimal_places        


class AddValueForm(LocalizeableForm):

    localizeable_fields = ['value']
    
    generic_field_id = forms.IntegerField(widget=forms.HiddenInput)
    generic_value_type = forms.CharField()
    value = forms.CharField(max_length=TEXT_LENGTH_RESTRICTIONS['GenericValues']['choice']) # this is not the GenericValues reference


from app_kit.models import MetaAppGenericContent
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import BLANK_CHOICE_DASH


class GenericFormChoicesMixin:

    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.load_generic_form_choices()

    def load_generic_form_choices(self):
        # get all forms of this app
        generic_form_ctype = ContentType.objects.get_for_model(GenericForm)

        generic_contents = MetaAppGenericContent.objects.filter(meta_app=self.meta_app,
                                                                content_type=generic_form_ctype)

        generic_forms = GenericForm.objects.filter(pk__in=generic_contents.values_list('object_id', flat=True))
        

        if not generic_forms.exists():
            choices = [('', _('You have no observation forms yet.'))]

        else:
            generic_form_choices = []
            for generic_form in generic_forms:
                
                choice = (
                    str(generic_form.uuid), generic_form.name
                )
                generic_form_choices.append(choice)

                self.uuid_to_instance[str(generic_form.uuid)] = generic_form
                
            choices = BLANK_CHOICE_DASH + generic_form_choices

        self.fields[self.generic_form_choicefield].choices = choices


from app_kit.forms import GenericContentOptionsForm
class GenericFormOptionsForm(GenericContentOptionsForm):

    is_default = forms.BooleanField(required=False,
                    label=_('Set this observation form as the default observation form of this app.'))

from django import forms
from app_kit.features.buttonmatrix.models import ButtonMatrix, ButtonMatrixButton, ButtonExtension
from django.utils.translation import gettext_lazy as _

from django.contrib.contenttypes.models import ContentType
from taxonomy.fields import TaxonField

from localcosmos_server.forms import LocalizeableModelForm

from app_kit.features.generic_forms.forms import DynamicField
from app_kit.features.generic_forms.models import GenericFieldToGenericForm

class MatrixButtonForm(LocalizeableModelForm):

    localizeable_fields = ['label']

    label = forms.CharField(max_length=50, required=False,
                help_text=_('If no label ist set for the matrix field, the name of the taxon will be the label.'))

    generic_form_fields = []
    
    taxon = TaxonField()

    def __init__(self, *args, **kwargs):
        self.generic_form = kwargs.pop('generic_form', None)
        initial = kwargs.pop('initial', {})

        if 'instance' in kwargs:
            extensions = ButtonExtension.objects.filter(generic_form=self.generic_form, button=kwargs['instance'])
            for extension in extensions:
                generic_field = extension.generic_field
                field_uuid = str(generic_field.uuid)
                if generic_field.field_class == 'MultipleChoiceField':
                    if field_uuid not in initial:
                        initial[field_uuid] = []
                    initial[field_uuid].append(extension.field_value)
                else:
                    initial[field_uuid] = extension.field_value
        
        super().__init__(initial=initial, *args, **kwargs)
        
        if self.instance and self.instance.label:
            self.fields['label'].initial = self.instance.label

        field_links = GenericFieldToGenericForm.objects.filter(generic_form=self.generic_form)
        for field_link in field_links:

            if field_link.generic_field.role == 'regular':
                dynamic_field = DynamicField(field_link, self.language)
                self.fields[dynamic_field.uuid] = dynamic_field.django_field
                self.generic_form_fields.append(field_link)

    def clean_label(self):
        label = self.cleaned_data['label']

        if label == '':
            label = None
            
        return label

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.taxon = self.cleaned_data['taxon']
        if commit:
            label = self.cleaned_data.get('label', None)
            instance.label = label
            instance.save()

        # update button extensions
        for field_link in self.generic_form_fields:

            generic_field = field_link.generic_field
            uuid = str(generic_field.uuid)
            
            if generic_field.field_class == 'MultipleChoiceField':

                extensions = ButtonExtension.objects.filter(generic_form=self.generic_form,
                                                            generic_field=generic_field, button=instance)
                
                existing = list(extensions.values_list('field_value', flat=True))
                
                for value in self.cleaned_data[uuid]:
                    if value not in existing:
                        buttonextension = ButtonExtension(
                            generic_form = self.generic_form,
                            generic_field = generic_field,
                            button = instance,
                            field_value = value,
                        )

                        buttonextension.save()
                    
                delete_values = list(set(existing) - set(self.cleaned_data[uuid]))
                for value in delete_values:
                    extension = ButtonExtension.objects.get(generic_form=self.generic_form,
                                            generic_field=generic_field, button=instance, field_value=value)
                    extension.delete()

                
            else:

                value = self.cleaned_data[uuid]
                
                buttonextension = ButtonExtension.objects.filter(generic_form=self.generic_form,
                                                           generic_field=generic_field, button=instance).first()

                if value:

                    if not buttonextension:
                        buttonextension = ButtonExtension(
                            generic_form = self.generic_form,
                            generic_field = generic_field,
                            button = instance,
                        )

                    buttonextension.field_value = value
                    buttonextension.save()
                    
                else:
                    if buttonextension:
                        buttonextension.delete()

            
        return instance

    class Meta:
        model = ButtonMatrixButton
        exclude = ('name_uuid', 'taxon_nuid', 'taxon_latname', 'taxon_author', 'taxon_source',
                   'taxon_include_descendants', 'translated_fields')
        
        widgets = {
            'button_matrix' : forms.HiddenInput,
            'row' : forms.HiddenInput,
            'column' : forms.HiddenInput,
        }


from app_kit.forms import GenericContentOptionsForm
from app_kit.features.generic_forms.forms import GenericFormChoicesMixin
from app_kit.features.generic_forms.models import GenericForm
from django.db.models.fields import BLANK_CHOICE_DASH

class ButtonMatrixOptionsForm(GenericFormChoicesMixin, GenericContentOptionsForm):

    generic_form_choicefield = 'generic_form'
    instance_fields = ['generic_form', 'generic_form_exposed_field']

    generic_form = forms.ChoiceField(required=False, label=_('Observation form'),
        help_text=_('Pushing a button of the matrix automatically creates an observation using this observation form.'))

    generic_form_exposed_field = forms.ChoiceField(required=False, label=_('observation form: displayed field'),
        help_text=_('Up to 1 field can be displayed above the button matrix for on-demand input.'))

    is_default = forms.BooleanField(required=False,
        label=_('Set this matrix as the default matrix (if more than one matrix present in the app).'))


    rows = forms.IntegerField()
    columns = forms.IntegerField()


    def __init__(self, *args, **kwargs):

        exposed_only = False
        generic_form = None

        # if ajax reload of exposed field form optons has been requestes - use this
        if 'exposed_field_form' in kwargs:
            generic_form = kwargs.pop('exposed_field_form')
            exposed_only = True

        super().__init__(*args, **kwargs)

        # only use the initial stuff if exposed iss False
        if exposed_only == False and 'generic_form' in self.initial:
            generic_form = GenericForm.objects.get(uuid=self.initial['generic_form'])

        # grab posted generic form, overrides exposed and initial
        if len(args) > 0 and 'generic_form' in args[0]:
            generic_form_uuid = args[0]['generic_form']
            if generic_form_uuid != '':
                generic_form = GenericForm.objects.get(uuid=generic_form_uuid)

        if generic_form is not None:
            # add possible fields
            field_choices = []
            for field in generic_form.fields.exclude(field_class__in=['TaxonField',
                'PointJSONField', 'MultipleChoiceField', 'DateTimeJSONField']):
                
                choice = (str(field.uuid), field.label)
                field_choices.append(choice)

                # add fields to instance dict
                self.uuid_to_instance[str(field.uuid)] = field
            
            choices = BLANK_CHOICE_DASH + field_choices


        else:
            choices = [('', _('Select an observation form first')),]

        
        self.fields['generic_form_exposed_field'].choices = choices


    def clean_generic_form(self):
        generic_form_uuid = self.cleaned_data.get('generic_form', None)
        if generic_form_uuid:

            generic_form = GenericForm.objects.get(uuid=generic_form_uuid)

            error_message = _('Observation forms for button matrices need a point field as geographic reference field')

            # check if the forms geographic_reference field is a pointfield
            geographic_reference_field = generic_form.geographic_reference_field()

            if not geographic_reference_field:
                raise forms.ValidationError(error_message)
            
            if geographic_reference_field and geographic_reference_field.field_class != 'PointJSONField':
                raise forms.ValidationError(error_message)
            
        return generic_form_uuid
        
        

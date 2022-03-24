from django.conf import settings
from django.db import models

from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from distutils.dir_util import copy_tree
from django.utils.translation import gettext_lazy as _

from app_kit.features.generic_forms.models import (GenericField, GenericForm, GenericFieldToGenericForm)

from app_kit.generic_content_validation import ValidationError, ValidationWarning

from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon

from app_it.taxonomy.lazy import LazyTaxonList, LazyTaxon

'''
    FEATURE BUTTONMATRIX
'''
# additional fields shown below the matrix
# or prefilled fields on a button

from app_kit.generic import GenericContent


class ButtonMatrix(GenericContent):

    # is_default = models.BooleanField(default=False) depends on app
    columns = models.IntegerField(default=4)
    rows = models.IntegerField(default=5)
    # sticky_number = models.BooleanField(default=False) lock button next to number

    ''' moved to JSON texts
    translations = TranslatedFields(
        name = models.CharField(max_length=255, null=True),
        slug = models.SlugField(unique=True, null=True),
    )
    '''

    '''
       Things that need checking:
       ERRORS:
       - number of columns or rows may not be 0
       WARNINGS:
       - button matrix without a button
    '''
    def validate(self, app):
        result = {
            'warnings' : [],
            'errors' : [],
        }

        # the matrix has to be present
        if self.columns == 0 or self.rows == 0:

            error = ValidationError(self, self, [_('The value 0 is entered for rows or columns.')])
            
            result['errors'].append(error)

        # there should be at least one button
        button_exists =  ButtonMatrixButton.objects.filter(button_matrix=self).exists()

        if not button_exists:

            warning = ValidationWarning(self, self, [_('Button matrix only has empty buttons.')])
            result['warnings'].append(warning)

        return result


    def validate_options(self, app):
        result = super().validate_options(app)

        # check if the generic_form is present in options
        generic_form_option = self.get_option(app, 'generic_form')
        if not generic_form_option:
            message = _('Button matrices need an observation form declared in the options.')
            error = ValidationError(self, self, [message])
            result['errors'].append(error)

        else: 
            generic_form = GenericForm.objects.filter(uuid=generic_form_option['uuid']).first()

            if not generic_form:
                message = _('The Observation Form you assigned to the Button Matrix has been deleted.')
                error = ValidationError(self, generic_form, [message])
                result['errors'].append(error)

            else:
                # generic form is available
                # check if the reference fields are of the correct type
                temporal_field_link = GenericFieldToGenericForm.objects.filter(generic_form=generic_form,
                                is_required=True, generic_field__role='temporal_reference').first()

                if temporal_field_link:
                    tempfield = temporal_field.generic_field
                    if tempfield.field_class != 'DateTimeJSONField':
                        message = _('The temporal reference field of the observation form you assigned to the button matrix has to be a "DateTimeJSONField".')
                        error = ValidationError(self, tempfield, [message])
                        result['errors'].append(error)

                    if tempfield.render_as != 'SelectDateTimeWidget':
                        message = _('The temporal reference field of the observation form you assigned to the button matrix needs the widget "SelectDateTimeWidget".')
                        error = ValidationError(self, tempfield, [message])
                        result['errors'].append(error)


                geographic_field_link = GenericFieldToGenericForm.objects.filter(generic_form=generic_form,
                                is_required=True, generic_field__role='geographic_reference').first()

                if geographic_field_link:
                    geofield = geographic_field_link.generic_field
                    if geofield.field_class != 'DateTimeJSONField':
                        message = _('The geographic reference Field of the observation form you assigned to the button matrix has to be a "PointJSONField".')
                        error = ValidationError(self, geofield, [message])
                        result['errors'].append(error)

                    if geofield.render_as != 'SelectDateTimeWidget':
                        message = _('The geographic reference field of the observation form you assigned to the button matrix needs the widget "MobilePositionInput".')
                        error = ValidationError(self, geofield, [message])
                        result['errors'].append(error)
                    
                    

                taxon_field_link = GenericFieldToGenericForm.objects.filter(generic_form=generic_form,
                                is_required=True, generic_field__role='taxonomic_reference').first()

                if taxon_field_link:
                    taxonfield = taxon_field_link.generic_field
                    if taxonfield.field_class != 'DateTimeJSONField':
                        message = _('The taxonomic reference field of the observation form you assigned to the button matrix has to be a "TaxonField".')
                        error = ValidationError(self, taxonfield, [message])
                        result['errors'].append(error)

                    if taxonfield.render_as != 'SelectDateTimeWidget':
                        message = _('The taxonomic reference field of the observation form you assigned to the button matrix needs the widget "BackboneTaxonAutocompleteWidget".')
                        error = ValidationError(self, taxonfield, [message])
                        result['errors'].append(error)

                
                
                # check if all required fields of the form are met by all buttons
                # required parameter is stored on the fieldlink between form and field
                field_links = GenericFieldToGenericForm.objects.filter(generic_form=generic_form,
                                is_required=True, generic_field__role='regular')

                for field_link in field_links:

                    # skip the exposed field - if any
                    exposed_field_option = self.get_option(app, 'generic_form_exposed_field')

                    # the option is just the uuid
                    if exposed_field_option and str(field_link.generic_field.uuid) == exposed_field_option['uuid']:
                        continue
                
                    buttons = ButtonMatrixButton.objects.filter(button_matrix=self)

                    for button in buttons:

                        extension_exists = ButtonExtension.objects.filter(generic_form=generic_form,
                                                generic_field=field_link.generic_field, button=button).exists()
                        
                        if not extension_exists:
                            message = _('Button row %(row_number)s column %(column_number)s of this button matrix needs to define a value for the observation form field %(label)s.' % { 'row_number': button.row,
                                                                                                                                                                                         'column_number' : button.column,
                                                                                                                                                                                         'label' :field_link.generic_field.label}) 
                            error = ValidationError(self, button, [message])
                            result['errors'].append(error)
                        
        return result

    
    def translation_complete(self, language_code):

        name = self.get_translated_field(language_code, 'name')
        
        if not name or len(name) == 0:
            return False

        ''' buttons without label are ok - the taxon is used then

        # check all buttons
        buttons = ButtonMatrixButton.objects.filter(button_matrix=self)
        for button in buttons:

            if not button.label or len(button.label) == 0:
                return False
        '''
        return True


    def taxa(self):
        button_content_type = ContentType.objects.get_for_model(ButtonMatrixButton)
        queryset = ButtonMatrixButton.objects.filter(button_matrix=self)
        taxonlist = LazyTaxonList(queryset)
        return taxonlist


    def higher_taxa(self):
        button_content_type = ContentType.objects.get_for_model(ButtonMatrixButton)
        queryset = ButtonMatrixButton.objects.filter(button_matrix=self, taxon_include_descendants=True)
        taxonlist = LazyTaxonList(queryset)
        return taxonlist

    class Meta:
        verbose_name = _("Button matrix")
        verbose_name_plural = _("Button matrices")


FeatureModel = ButtonMatrix

class ButtonMatrixButton(ModelWithRequiredTaxon):

    LazyTaxonClass = LazyTaxon

    button_matrix = models.ForeignKey(ButtonMatrix, on_delete=models.CASCADE)
    row = models.IntegerField() # starting with 1
    column = models.IntegerField() # starting with 1

    label = models.CharField(max_length=50, null=True)

    def extensions(self):
        return ButtonExtension.objects.filter(button=self)

    def __str__(self):
        current_language = self.get_current_language()

        label = self.get_translated_field(current_language, 'label')
        
        
        if self.label:
            return self.label

        return self.taxon_verbose(current_language)

    class Meta:
        unique_together = ('row', 'column', 'button_matrix')


class ButtonExtension(models.Model):
    button = models.ForeignKey(ButtonMatrixButton, on_delete=models.CASCADE)
    generic_form = models.ForeignKey(GenericForm, on_delete=models.CASCADE)
    generic_field = models.ForeignKey(GenericField, on_delete=models.CASCADE, related_name='buttonmatrixfield')
    field_value = models.CharField(max_length=255)

    def value(self):
        if self.generic_field.field_class == 'MultipleChoiceField':
            return ButtonExtension.objects.filter(button=self.button,
                    generic_field=self.generic_field).values_list('field_value', flat=True)
        else:
            return self.field_value
        
    # multiple entries are only allowed for multiple choice field
    def save(self, *args, **kwargs):
        if self.generic_field.field_class != 'MultipleChoiceField':
            if not self.pk and ButtonExtension.objects.filter(button=self.button, generic_field=self.generic_field).exists():
                raise ValueError('An entry for button %s and field %s already exists and the field is not of type MultipleChoiceField' % (self.button.id, self.generic_field.id))
        return super().save(*args, **kwargs)

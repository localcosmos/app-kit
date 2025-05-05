'''
    Fields are strictly bound to GenericForms. If a GenericForm wants to import a field, the field will be cloned
'''
from django.db import models
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.translation import gettext_lazy as _

import uuid

from app_kit.generic import GenericContent, AppContentTaxonomicRestriction

from taxonomy.lazy import LazyTaxonList


DJANGO_FIELD_WIDGETS = (
    ('CheckboxInput', _('Checkbox')), #no default value (=False)
    ('TextInput', _('Single line text input')), #no default value (=null)
    ('Textarea', _('Multi-line text input')), #no default value (=null)
    ('NumberInput', _('Number field')), #no default value (=null)
    ('MobileNumberInput', _('Number input with +/- buttons')),
    ('HiddenInput', _('Hidden field')),
    ('Select', _('Dropdown')),
    ('CheckboxSelectMultiple', _('Multiple choice')),
    ('RadioSelect', _('Radio')),
    ('SelectDateTimeWidget', _('Date and time with autofill')), # JSONWidget
    ('MobilePositionInput', _('GPS-supported point input with map')), # JSONWidget
    ('PointOrAreaInput', _('GPS-supported point or area input with map')), # JSONWidget
    ('BackboneTaxonAutocompleteWidget', _('Taxon input with backend search')),
    ('CameraAndAlbumWidget', _('Camera and album')),
    ('FixedTaxonWidget', _('Fixed taxon')),
    ('SelectTaxonWidget', _('Select taxon widget')),
)

DJANGO_FIELD_CLASSES = (
    ('BooleanField', _('Checkbox field')),
    ('CharField', _('Text field')),
    ('ChoiceField', _('Choice field')),
    ('DecimalField', _('Decimal number field (fixed precision)')),
    ('FloatField', _('Floating number field (precision not fixed)')),
    ('IntegerField', _('Integer field')),
    ('MultipleChoiceField', _('Multiple choice field')),
    ('DateTimeJSONField', _('Datetime field')),
    ('TaxonField', _('Taxon field')),
    ('SelectTaxonField', _('Select taxon field')),
    ('PointJSONField', _('Point field')),
    #('GeoJSONField', _('Geometry field')),
    ('PictureField', _('Image field')),
)

NUMBER_FIELDS = ['DecimalField', 'FloatField', 'IntegerField']

DEFAULT_WIDGETS = {
    'BooleanField' : 'CheckboxInput',
    'CharField' : 'TextInput',
    'ChoiceField' : 'Select',
    'DecimalField' : 'MobileNumberInput',
    'FloatField': 'MobileNumberInput',
    'IntegerField' : 'MobileNumberInput',
    'MultipleChoiceField' : 'CheckboxSelectMultiple',
    'DateTimeJSONField' : 'SelectDateTimeWidget', # JSONField
    'PointJSONField' : 'MobilePositionInput', # JSONField
    'TaxonField' : 'BackboneTaxonAutocompleteWidget',
    'SelectTaxonField': 'SelectTaxonWidget',
    'PictureField' : 'CameraAndAlbumWidget',
    #'GeoJSONField' : 'PointOrAreaInput',
}

ALLOWED_WIDGETS = {
    'BooleanField' : ['CheckboxInput'],
    'CharField' : ['TextInput', 'Textarea'],
    'ChoiceField' : ['Select'],
    'DecimalField' : ['MobileNumberInput'],
    'FloatField': ['MobileNumberInput'],
    'IntegerField' : ['MobileNumberInput'],
    'MultipleChoiceField' : ['CheckboxSelectMultiple'],
    'DateTimeJSONField' : ['SelectDateTimeWidget'], # JSONField + JSONWidget
    'PointJSONField' : ['MobilePositionInput'], # JSONField + JSONWidget
    #'GeoJSONField' : ['PointOrAreaInput'], # JSONField + JSONWidget
    'TaxonField' : ['BackboneTaxonAutocompleteWidget', 'FixedTaxonWidget'],
    'SelectTaxonField' : ['SelectTaxonWidget'],
    'PictureField' : ['CameraAndAlbumWidget'],
}

FIELDCLASS_DATATYPE = {
    'BooleanField' : 'bool',
    'CharField' : 'text',
    'ChoiceField' : 'text',
    'DecimalField' : 'number',
    'FloatField' : 'number',
    'IntegerField' : 'number',
    'MultipleChoiceField' : 'text',
    'DateTimeJSONField' : 'json',
    'TaxonField' : 'json',
    'PointJSONField' : 'json',
    #'GeoJSONField' : 'json',
    'PictureField' : 'json',
    'SelectTaxonField' : 'json',
}

class GenericFormVersionBumpMixin:
    
    def check_generic_form_version_bump(self, generic_field):

        form_links = GenericFieldToGenericForm.objects.filter(generic_field=generic_field)
        for form_link in form_links:
            generic_form = form_link.generic_form

            generic_form.check_version()        



class GenericForm(GenericContent):

    fields = models.ManyToManyField('GenericField', through='GenericFieldToGenericForm')

    taxonomic_restrictions = GenericRelation(AppContentTaxonomicRestriction)

    def get_primary_localization(self, meta_app=None):
        locale = super().get_primary_localization(meta_app)

        for generic_field in self.fields.all():
            
            if generic_field.label:
                locale[generic_field.label] = generic_field.label

            if generic_field.help_text:
                locale[generic_field.help_text] = generic_field.help_text

            
            # min, max and decimal_places are translated automatically
            generic_values = GenericValues.objects.filter(generic_field=generic_field, value_type='choice')

            for generic_value in generic_values:

                if generic_value.name:
                    locale[generic_value.name] = generic_value.name
        
        return locale

    # taxa returns all taxa and is for backbone collections - and only for Subclasses of
    # GenericContent
    def _taxon_query_base(self):

        form_content_type = ContentType.objects.get_for_model(GenericForm)

        query = Q()
        query.add(Q(content_type=form_content_type, object_id=self.id), Q.OR)

        field_content_type = ContentType.objects.get_for_model(GenericField)

        field_ids = GenericFieldToGenericForm.objects.filter(generic_form=self).values_list('generic_field_id',
                                                                                            flat=True)
        query.add(Q(content_type=field_content_type, object_id__in=field_ids), Q.OR)

        return query
        
    
    def taxa(self):

        query = self._taxon_query_base()
        
        queryset = AppContentTaxonomicRestriction.objects.filter(query).distinct('taxon_latname')
        taxonlist = LazyTaxonList(queryset)
        
        return taxonlist

    def higher_taxa(self):
        query = self._taxon_query_base()
        query.add(Q(taxon_include_descendants=True), Q.AND)
        queryset = AppContentTaxonomicRestriction.objects.filter(query).distinct('taxon_latname')
        taxonlist = LazyTaxonList(queryset)

        return taxonlist


    # shortcuts
    def get_field_by_role(self, role):
        field = GenericFieldToGenericForm.objects.filter(generic_form=self,
                                                         generic_field__role=role).first()

        if field:
            return field.generic_field

        return None


    def taxonomic_reference_field(self):
        return self.get_field_by_role('taxonomic_reference')
    
    def geographic_reference_field(self):
        return self.get_field_by_role('geographic_reference')

    def temporal_reference_field(self):
        return self.get_field_by_role('temporal_reference')


    class Meta:
        verbose_name = _('Observation form')
        verbose_name_plural = _('Observation forms')


FeatureModel = GenericForm

REFERENCE_FIELD_TYPES = (
    'temporal_reference',
    'taxonomic_reference',
    'geographic_reference',
)

FIELD_ROLES = (
    ('temporal_reference', _('Temporal Reference')),
    ('taxonomic_reference', _('Taxon')),
    ('geographic_reference', _('Geographic Reference')),
    ('regular', _('Regular')),
)


FIELD_OPTIONS = {
    'DecimalField' : ['min_value', 'max_value', 'decimal_places', 'step', 'initial', 'unit'],
    'FloatField' : ['min_value', 'max_value', 'step', 'initial', 'unit'],
    'IntegerField' : ['min_value', 'max_value', 'step', 'initial', 'unit'],
    'DateTimeJSONField' : ['datetime_mode'],
}

NON_DJANGO_FIELD_OPTIONS = ['step', 'unit', 'datetime_mode']

'''
    fields can be shared across forms
    - somehow check language, generic_forms primary_language have to be the same
'''
class GenericField(GenericFormVersionBumpMixin, models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    field_class = models.CharField(max_length=255, choices=DJANGO_FIELD_CLASSES) # forms.XYfields according to django
    render_as = models.CharField(max_length=255, choices=DJANGO_FIELD_WIDGETS) # django widgets
    version = models.IntegerField(default=1)
    
    role = models.CharField(max_length=50, choices=FIELD_ROLES, default='regular')

    options = models.JSONField(null=True) # options that apply only to certain field classes like min, max, decimal_places, unit

    label = models.CharField(max_length=255)
    help_text = models.CharField(max_length=255, null=True)

    taxonomic_restrictions = GenericRelation(AppContentTaxonomicRestriction)
    

    def get_option(self, option):
        if self.options and option in self.options:
            return self.options[option]

        return None
    
    
    def value(self, value_type):

        val = GenericValues.objects.filter(generic_field=self, value_type=value_type).first()

        if val:
            return val.value()

        return None

    def choices(self):
        
        if self.field_class != 'ChoiceField' and self.field_class != 'MultipleChoiceField':
            return []

        choices = GenericValues.objects.filter(generic_field=self, value_type='choice').order_by('position')
        return choices


    def save(self, generic_form, *args, **kwargs):
        # if it is a new field, check the roles
        if self.role != 'regular' and not self.pk:
            exists = GenericFieldToGenericForm.objects.filter(generic_form=generic_form,
                                                              generic_field__role=self.role).exists()
            if exists:
                raise ValueError('This form already has got one field with the role {0}'.format(self.role))
        super().save(*args, **kwargs)

        self.check_generic_form_version_bump(self)

    def delete(self, *args, **kwargs):
        self.check_generic_form_version_bump(self)
        super().delete(*args, **kwargs)
        

    def __str__(self):
        return '{0}'.format(self.label)
    
    class Meta:
        verbose_name = _('Observation Form Field')
        verbose_name_plural = _('Observation Form Fields')


'''
    A field should be usable in different forms
    - the values and options are always the same, independant of the form
    - the role is also independant from the form. A field with the role 'taxon' will always be of the role 'taxon'
    - parameters like required and position depend on the form
'''
class GenericFieldToGenericForm(models.Model):

    generic_form = models.ForeignKey(GenericForm, on_delete=models.CASCADE)
    generic_field = models.ForeignKey(GenericField, on_delete=models.CASCADE)

    is_required = models.BooleanField(default=False)
    is_sticky = models.BooleanField(default=False)
    position = models.IntegerField(default=0)


    def save(self, *args, **kwargs):
        # if it is a new field, check the roles
        if self.generic_field.role == 'taxonomic_reference':
            self.position = -3
        elif self.generic_field.role == 'geographic_reference':
            self.position = -2
        elif self.generic_field.role == 'temporal_reference':
            self.position = -1
        
        if self.generic_field.role != 'regular' and not self.pk:
            exists = GenericFieldToGenericForm.objects.filter(generic_form=self.generic_form,
                                                              generic_field__role=self.generic_field.role).exists()
            if exists:
                raise ValueError('This form already has got one field with the role %s' % self.generic_field.role)

        super().save(*args, **kwargs)

        self.generic_form.check_version()

    def delete(self, *args, **kwargs):
        self.generic_form.check_version()
        super().delete(*args, **kwargs)
        

    class Meta:
        unique_together = ('generic_form', 'generic_field')
        ordering = ['position', 'id']


'''
    checkboxes neither have FieldValues nor FieldValueLocale, GenericValues is an optional restriction
    GenericValues are strictly bound to a GenericField and are not reusable by other fields
    GenericValues have either a text value or a number value, making good sql queries possible <- only in dataset data
'''
VALUE_TYPES = (
    ('choice', _('Choice')),
)

class GenericValues(GenericFormVersionBumpMixin, models.Model):
    generic_field = models.ForeignKey(GenericField, on_delete=models.CASCADE)
    text_value = models.CharField(max_length=255) # numbers need a cast when used, depending on generic_field.field_class
    value_type = models.CharField(max_length=20, choices=VALUE_TYPES)
    is_default = models.BooleanField(default=False)
    position = models.IntegerField(default=0)

    name = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if self.is_default == True:
            old_defaults = GenericValues.objects.filter(generic_field=self.generic_field, is_default=True)
            for default in old_defaults:
                default.is_default = False
                default.save()

        super().save(*args, **kwargs)

        self.check_generic_form_version_bump(self.generic_field)

    
    def delete(self, *args, **kwargs):
        self.check_generic_form_version_bump(self.generic_field)
        super().delete(*args, **kwargs)


    def value(self):
        value_datatype = FIELDCLASS_DATATYPE[self.generic_field.field_class]
        casted_value = self.text_value
        if value_datatype == 'number':
            
            if self.generic_field.field_class == 'IntegerField':
                casted_value = int(float(casted_value)) # it could be 5.0
            else:
                casted_value = float(casted_value)
                
        return casted_value


    class Meta:
        ordering = ['position', 'id']

from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

# GENERIC FORMS
from app_kit.features.generic_forms.models import (GenericForm, GenericField, GenericValues,
                                                       GenericFieldToGenericForm)

from app_kit.utils import underscore_to_camelCase

'''
    generates a json according to GenericFormJSON specification v1
    - do not store label etc texts directly in the form, use i18next to look up the localized texts
'''
REFERENCE_FIELD_ROLES = ['taxonomic_reference', 'geographic_reference', 'temporal_reference']

class GenericFormJSONBuilder(JSONBuilder):

    def build_features_json_entry(self):
        
        features_json_entry = super().build_features_json_entry()

        taxonomic_restrictions = self.get_taxonomic_restriction(self.generic_content)
        features_json_entry['taxonomicRestrictions'] = taxonomic_restrictions

        return features_json_entry

    
    def build(self):

        generic_form_json = self._build_common_json()

        generic_form = self.generic_content
        generic_form_json = self._add_json_fields(generic_form, generic_form_json)

        return generic_form_json


    def _add_json_fields(self, generic_form, generic_form_json):

        taxonomic_restrictions = self.get_taxonomic_restriction(generic_form)

        generic_form_json.update({
            'fields' : [],
            'taxonomicRestrictions' : taxonomic_restrictions,
        })

        field_links = GenericFieldToGenericForm.objects.filter(generic_form=generic_form).order_by('position')

        for generic_field_link in field_links:

            generic_field_dic = self._create_generic_form_field_dic(generic_field_link)
            generic_field = generic_field_link.generic_field

            generic_form_json['fields'].append(generic_field_dic)

            if generic_field.role in REFERENCE_FIELD_ROLES:
                key = self.to_camel_case(generic_field_dic['role'])
                generic_form_json[key] = generic_field_dic['uuid']

        return generic_form_json


    '''
    create json for a form field
    '''
    def _create_generic_form_field_dic(self, generic_field_link):
        generic_field = generic_field_link.generic_field

        widget = generic_field.render_as

        taxonomic_restriction = self.get_taxonomic_restriction(generic_field)

        is_required = generic_field_link.is_required

        if generic_field.role in ['geographic_reference', 'temporal_reference']:
            is_required = True

        field_dic = {
            'uuid' : str(generic_field.uuid),
            'fieldClass' : generic_field.field_class,
            'version' : generic_field.version,
            'role' : underscore_to_camelCase(generic_field.role),
            'definition' : {
                'widget' : widget,
                'required' : is_required,
                'isSticky' : generic_field_link.is_sticky,
                'label' : generic_field.label,
                'helpText' : generic_field.help_text,
                'initial' : None,
                'unit' : generic_field.get_option('unit'),
            },
            'position' : generic_field_link.position,
            # 'options' : generic_field.options, # moved to widgetAttrs
            'widgetAttrs' : {},
            'taxonomicRestrictions' : taxonomic_restriction,
        }

        if generic_field.field_class == 'DateTimeJSONField':
            # default mode
            field_dic['definition']['mode'] = 'datetime-local'

            if generic_field.options and 'datetime_mode' in generic_field.options:
                field_dic['definition']['mode'] = generic_field.options['datetime_mode']

        # generate widget_attrs from options
        if generic_field.field_class in ['DecimalField', 'FloatField', 'IntegerField']:
            if generic_field.options:

                # defaults
                min_value = None
                max_value = None
                initial = None

                if 'min_value' in generic_field.options:
                    min_value = generic_field.options['min_value']
                    field_dic['widgetAttrs']['min'] = min_value

                if 'max_value' in generic_field.options:
                    max_value = generic_field.options['max_value']
                    field_dic['widgetAttrs']['max'] = max_value

                if 'initial' in generic_field.options:
                    initial = generic_field.options['initial']
                field_dic['definition']['initial'] = initial

                # apply the step - necessary for html in-browser validation of forms
                # default and fallback
                step = 1

                if generic_field.field_class == 'FloatField' or generic_field.field_class == 'DecimalField':
                    #default
                    step = 0.01

                    if 'decimal_places' in generic_field.options:
                        # both pow and math.pow fail for pow(0.1, 2) which is ridiculous
                        decimal_places = generic_field.options['decimal_places']

                        if decimal_places == 0:
                            step = 1
                        elif decimal_places > 0:
                            step = float('0.{0}1'.format('0' * (decimal_places-1)))

                field_dic['widgetAttrs']['step'] = step

        values = GenericValues.objects.filter(generic_field=generic_field).order_by('position')

        for db_value in values:

            if db_value.value_type == 'choice':

                if 'choices' not in field_dic['definition']:
                    field_dic['definition']['choices'] = []

                # choice needs to respect singlelanguage - translations in locale file
                choice = [db_value.text_value, db_value.text_value]

                field_dic['definition']['choices'].append(choice)

                if db_value.is_default:
                    field_dic['definition']['initial'] = db_value.text_value

            else:
                value_dic = {
                    'textValue' : db_value.text_value,
                    'valueType' : db_value.value_type,
                    'isDefault' : db_value.is_default,
                    'name' : db_value.name,
                }

                field_dic['values'].append(value_dic)


        
        if 'choices' in field_dic['definition']:

            # prepend the empty choice if field isnt required
            if generic_field.field_class != 'MultipleChoiceField' and generic_field_link.is_required == False:

                empty_label = '-----'
                field_dic['definition']['choices'].insert(0,['', empty_label])
                

        return field_dic

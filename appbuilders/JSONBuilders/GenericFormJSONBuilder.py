from app_kit.appbuilders.JSONBuilders.JSONBuilder import JSONBuilder

# GENERIC FORMS
from app_kit.features.generic_forms.models import (GenericForm, GenericField, GenericValues,
                                                       GenericFieldToGenericForm)


'''
    generates a json according to GenericFormJSON specification v1
    - do not store label etc texts directly in the form, use i18next to look up the localized texts
'''
class GenericFormJSONBuilder(JSONBuilder):

    
    def build(self):

        generic_form_json = self._build_common_json()

        generic_form = self.generic_content
        generic_form_json = self._add_json_fields(generic_form, generic_form_json)

        return generic_form_json


    def _add_json_fields(self, generic_form, generic_form_json):

        taxonomic_restriction = self.get_taxonomic_restriction(generic_form)

        generic_form_json.update({
            'fields' : [],
            'taxonomic_restriction' : taxonomic_restriction,
        })

        field_links = GenericFieldToGenericForm.objects.filter(generic_form=generic_form).order_by('position')

        for generic_field_link in field_links:

            generic_field_dic = self._create_generic_form_field_dic(generic_field_link)
            generic_field = generic_field_link.generic_field

            generic_form_json['fields'].append(generic_field_dic)

            if generic_field_dic['role'] in ['taxonomic_reference', 'geographic_reference', 'temporal_reference']:
                key = generic_field_dic['role']
                generic_form_json[key] = generic_field_dic['uuid']

        return generic_form_json


    '''
    create json for a form field
    '''
    def _create_generic_form_field_dic(self, generic_field_link):
        generic_field = generic_field_link.generic_field

        widget = generic_field.render_as

        taxonomic_restriction = self.get_taxonomic_restriction(generic_field)

        field_dic = {
            'uuid' : str(generic_field.uuid),
            'field_class' : generic_field.field_class,
            'version' : generic_field.version,
            'role' : generic_field.role,
            'definition' : {
                'widget' : widget,
                'required' : generic_field_link.is_required,
                'is_sticky' : generic_field_link.is_sticky,
                'label' : generic_field.label,
                'help_text' : generic_field.help_text,
                'initial' : None,
            },
            'position' : generic_field_link.position,
            'options' : generic_field.options, # contains widget_attrs and other stuff
            'widget_attrs' : {},
            'taxonomic_restriction' : taxonomic_restriction,
        }

        if generic_field.field_class == 'SelectDateTime':
            # default mode
            field_dic['widget_attrs']['mode'] = 'datetime'

            if generic_field.options and 'datetime_mode' in generic_field.options:
                field_dic['widget_attrs']['mode'] = generic_field.options['datetime_mode']

        # generate widget_attrs from options
        if generic_field.field_class in ['DecimalField', 'FloatField', 'IntegerField']:
            if generic_field.options:

                # defaults
                min_vale = None
                max_value = None

                if 'min_value' in generic_field.options:
                    min_value = generic_field.options['min_value']
                    field_dic['widget_attrs']['min'] = min_value

                if 'max_value' in generic_field.options:
                    max_value = generic_field.options['max_value']
                    field_dic['widget_attrs']['max'] = max_value

                # apply the step - necessary for html in-browser validation of forms
                # default and fallback
                step = '1'

                if generic_field.field_class == 'FloatField' or generic_field.field_class == 'DecimalField':
                    #default
                    step = '0.01'

                    if 'decimal_places' in generic_field.options:
                        # both pow and math.pow fail for pow(0.1, 2) which is ridiculous
                        decimal_places = generic_field.options['decimal_places']

                        if decimal_places == 0:
                            step = '1'
                        elif decimal_places > 0:
                            step = '0.%s1' % ('0' * (decimal_places-1))

                field_dic['widget_attrs']['step'] = step

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
                    'text_value' : db_value.text_value,
                    'value_type' : db_value.value_type,
                    'is_default' : db_value.is_default,
                    'name' : db_value.name,
                }

                field_dic['values'].append(value_dic)


        
        if 'choices' in field_dic['definition']:

            # prepend the empty choice if field isnt required
            if generic_field.field_class != 'MultipleChoiceField' and generic_field_link.is_required == False:

                empty_label = '-----'
                field_dic['definition']['choices'].insert(0,['', empty_label])
                

        return field_dic

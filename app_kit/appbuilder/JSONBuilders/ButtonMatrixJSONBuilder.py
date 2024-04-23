from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.buttonmatrix.models import ButtonMatrixButton, ButtonExtension

class ButtonMatrixJSONBuilder(JSONBuilder):

    def build(self, languages):

        button_matrix = self.generic_content
        button_matrix.set_current_language(language_code)

        # this has options and global_options
        button_matrix_json = self._build_common_json(languages)

        button_matrix_json.update({
            'rows' : [],
            'total_rows' : button_matrix.rows,
            'total_columns' : button_matrix.columns,
        })

        for row in range(1, button_matrix.rows+1):

            row_dic = {
                'columns' : []
            }

            for i in range(1, button_matrix.columns+1): # the top left is 1.1
                row_dic['columns'].append(None)

            # do not include out of bounds buttons
            buttons = ButtonMatrixButton.objects.filter(button_matrix=button_matrix, row=row,
                                                        column__lt=button_matrix.columns+1).order_by('column')

            for button in buttons:
                button.set_current_language(language_code)
                
                # label is optional. if no label is given, the taxon is the label
                button_dic = {
                    'row' : button.row,
                    'column' : button.column,
                    'taxon' : {
                        'taxon_source' : button.taxon_source,
                        'taxon_latname' : button.taxon_latname,
                        'taxon_author' : button.taxon_author,
                        'taxon_vernacular' : button.taxon.vernacular(language=language_code),
                        'name_uuid' : button.name_uuid,
                        'taxon_nuid' : button.taxon_nuid,
                    },
                    'label' : button.label,
                    'extensions' : {},
                    'id' : button.id,
                }

                if not button.label:

                    if button.taxon.vernacular(language=language_code):
                        button_dic['label'] = button.taxon.vernacular(language=language_code)
                    else:
                        button_dic['label'] = button.taxon_latname


                # fill extensions
                extensions = ButtonExtension.objects.filter(button=button)
                for extension in extensions:

                    extension_field = extension.generic_field

                    generic_field_uuid = str(extension_field.uuid)

                    if extension_field.field_class == 'MultipleChoiceField':
                        if generic_field_uuid not in button_dic['extensions']:
                            button_dic['extensions'][generic_field_uuid] = []
                        button_dic['extensions'][generic_field_uuid].append(extension.field_value)
                        
                    else:
                        button_dic['extensions'][generic_field_uuid] = extension.field_value
                
                row_dic['columns'][button.column-1] = button_dic

            button_matrix_json['rows'].append(row_dic)

        # button_matrix_json is now ready for dumping
        return button_matrix_json

        

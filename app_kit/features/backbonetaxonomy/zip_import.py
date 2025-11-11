from django.utils.translation import gettext_lazy as _

from app_kit.generic_content_zip_import import GenericContentZipImporter

from app_kit.features.backbonetaxonomy.models import TaxonRelationshipType, TaxonRelationship

TAXON_RELATIONSHIP_TYPES_SHEET_NAME = 'Taxon Relationship Types'
TAXON_RELATIONSHIPS_SHEET_NAME = 'Taxon Relationships'

'''
    Taxonomy as Spreadsheet
    - only supports taxon relationships for now
'''

class BackbonetaxonomyZipImporter(GenericContentZipImporter):
    
    images_sheet_name = None
    external_media_sheet_name = None
    
    required_sheet_names = [
        TAXON_RELATIONSHIP_TYPES_SHEET_NAME,
        TAXON_RELATIONSHIPS_SHEET_NAME
    ]

    def validate_definition_rows(self):

        taxon_relationship_types_sheet = self.get_sheet_by_name(TAXON_RELATIONSHIP_TYPES_SHEET_NAME)

        for row_index, row in enumerate(taxon_relationship_types_sheet.iter_rows(max_row=1), 1):

            cell_A1_value = self.get_stripped_cell_value_lowercase(row[0].value)
            cell_B1_value = self.get_stripped_cell_value_lowercase(row[1].value)
            cell_C1_value = self.get_stripped_cell_value_lowercase(row[2].value)

            if cell_A1_value != 'relationship name':
                message = _('Cell content has to be "Relationship Name", not %(value)s') % {
                    'value': row[0].value
                }
                self.add_cell_error(self.workbook_filename, taxon_relationship_types_sheet.title, 'A', 0, message)


            if cell_B1_value != 'taxon role (optional)':
                message = _('Cell content has to be "Taxon Role (optional)", not %(value)s') % {
                    'value': row[1].value
                }
                self.add_cell_error(self.workbook_filename, taxon_relationship_types_sheet.title, 'B', 0, message)


            if cell_C1_value != 'related taxon role (optional)':
                message = _('Cell content has to be "Related Taxon Role (optional)", not %(value)s') % {
                    'value' : row[2].value
                }
                self.add_cell_error(self.workbook_filename, taxon_relationship_types_sheet.title, 'C', 0, message)
                
        taxon_relationships_sheet = self.get_sheet_by_name(TAXON_RELATIONSHIPS_SHEET_NAME)
        for row_index, row in enumerate(taxon_relationships_sheet.iter_rows(max_row=2), 1):
            
            if row_index == 1:
            
                cell_A1_value = self.get_stripped_cell_value_lowercase(row[0].value)
                cell_B1_value = self.get_stripped_cell_value_lowercase(row[1].value)
                cell_C1_value = self.get_stripped_cell_value_lowercase(row[2].value)
                cell_D1_value = self.get_stripped_cell_value_lowercase(row[3].value)
                cell_E1_value = self.get_stripped_cell_value_lowercase(row[4].value)
                cell_F1_value = self.get_stripped_cell_value_lowercase(row[5].value)
                cell_G1_value = self.get_stripped_cell_value_lowercase(row[6].value)
                cell_H1_value = self.get_stripped_cell_value_lowercase(row[7].value)

                if cell_A1_value not in ['', None]:
                    message = _('Cell has to be empty, not %(value)s') % {
                        'value': row[0].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'A', 0, message)


                if cell_B1_value != 'taxon':
                    message = _('Cell content has to be "Taxon", not %(value)s') % {
                        'value': row[1].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'B', 0, message)


                if cell_C1_value != 'taxon':
                    message = _('Cell content has to be "Taxon", not %(value)s') % {
                        'value' : row[2].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'C', 0, message)
                    
                if cell_D1_value != 'taxon':
                    message = _('Cell content has to be "Taxon", not %(value)s') % {
                        'value' : row[3].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'D', 0, message)
                    
                if cell_E1_value != 'related taxon':
                    message = _('Cell content has to be "Related Taxon", not %(value)s') % {
                        'value' : row[4].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'E', 0, message)
                
                if cell_F1_value != 'related taxon':
                    message = _('Cell content has to be "Related Taxon", not %(value)s') % {
                        'value' : row[5].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'F', 0, message)
                    
                if cell_G1_value != 'related taxon':
                    message = _('Cell content has to be "Related Taxon", not %(value)s') % {
                        'value' : row[6].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'G', 0, message)
                    
                if cell_H1_value not in ['', None]:
                    message = _('Cell has to be empty, not %(value)s') % {
                        'value': row[7].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'H', 0, message)
                    
                    
            if row_index == 2:
                
                cell_A2_value = self.get_stripped_cell_value_lowercase(row[0].value)
                cell_B2_value = self.get_stripped_cell_value_lowercase(row[1].value)
                cell_C2_value = self.get_stripped_cell_value_lowercase(row[2].value)
                cell_D2_value = self.get_stripped_cell_value_lowercase(row[3].value)
                cell_E2_value = self.get_stripped_cell_value_lowercase(row[4].value)
                cell_F2_value = self.get_stripped_cell_value_lowercase(row[5].value)
                cell_G2_value = self.get_stripped_cell_value_lowercase(row[6].value)
                cell_H2_value = self.get_stripped_cell_value_lowercase(row[7].value)
                
                if cell_A2_value != 'relationship':
                    message = _('Cell content has to be "Relationship", not %(value)s') % {
                        'value': row[0].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'A', 1, message)
                    
                if cell_B2_value != 'scientific name':
                    message = _('Cell content has to be "Scientific Name", not %(value)s') % {
                        'value': row[1].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'B', 1, message)
                    
                if cell_C2_value != 'author (optional)':
                    message = _('Cell content has to be "Author (optional)", not %(value)s') % {
                        'value': row[2].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'C', 1, message)


                if cell_D2_value != 'taxonomic source':
                    message = _('Cell content has to be "Taxonomic Source", not %(value)s') % {
                        'value': row[3].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'D', 1, message)
                    
                if cell_E2_value != 'scientific name':
                    message = _('Cell content has to be "Scientific Name", not %(value)s') % {
                        'value': row[4].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'E', 1, message)
                    
                if cell_F2_value != 'author (optional)':
                    message = _('Cell content has to be "Author (optional)", not %(value)s') % {
                        'value': row[5].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'F', 1, message)
                    
                if cell_G2_value != 'taxonomic source':
                    message = _('Cell content has to be "Taxonomic Source", not %(value)s') % {
                        'value': row[6].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'G', 1, message)
                
                if cell_H2_value != 'description (optional)':
                    message = _('Cell content has to be "Description (optional)", not %(value)s') % {
                        'value': row[7].value
                    }
                    self.add_cell_error(self.workbook_filename, taxon_relationships_sheet.title, 'H', 1, message)

    # content, not definition rows
    def validate_taxon_relationship_types_sheet(self):
        
        taxon_relationship_types_sheet = self.get_sheet_by_name(TAXON_RELATIONSHIP_TYPES_SHEET_NAME)
        
        if not taxon_relationship_types_sheet:
            message = _('Sheet "%(sheet_name)s" not found in the spreadsheet') % {
                'sheet_name': TAXON_RELATIONSHIP_TYPES_SHEET_NAME,
            }
            self.errors.append(message)
        
        else:
            for row_index, row in enumerate(taxon_relationship_types_sheet.iter_rows(min_row=2), 1):
                relationship_name = self.get_stripped_cell_value(row[0].value)
                taxon_role = self.get_stripped_cell_value(row[1].value)
                related_taxon_role = self.get_stripped_cell_value(row[2].value)
                
                # skip empty rows
                if not relationship_name and not taxon_role and not related_taxon_role:
                    continue
                
                # respect empty rows
                if not relationship_name and (taxon_role or related_taxon_role):
                    message = _('Relationship Name is required.')
                    self.add_cell_error(self.workbook_filename, TAXON_RELATIONSHIP_TYPES_SHEET_NAME, 'A', row_index + 2, message)

                if taxon_role and not related_taxon_role:
                    message = _('Related Taxon Role is required if Taxon Role is provided.')
                    self.add_cell_error(self.workbook_filename, TAXON_RELATIONSHIP_TYPES_SHEET_NAME, 'C', row_index + 2, message)
        
    # get the type from the sheet
    def get_taxon_relationship_type_by_name(self, name):
        
        taxon_relationship_types_sheet = self.get_sheet_by_name(TAXON_RELATIONSHIP_TYPES_SHEET_NAME)
        if taxon_relationship_types_sheet:
            for row in taxon_relationship_types_sheet.iter_rows(min_row=2):
                relationship_name = self.get_stripped_cell_value(row[0].value)
                if relationship_name == name:
                    taxon_role = self.get_stripped_cell_value(row[1].value)
                    related_taxon_role = self.get_stripped_cell_value(row[2].value)
                    return {
                        'name': relationship_name,
                        'taxon_role': taxon_role,
                        'related_taxon_role': related_taxon_role
                    }
        return None
        
    def validate_taxon_relationship_row(self, row, row_index):
        relationship_name = self.get_stripped_cell_value(row[0].value)
        taxon_latname = self.get_stripped_cell_value(row[1].value)
        taxon_author = self.get_stripped_cell_value(row[2].value)
        taxon_source = self.get_stripped_cell_value(row[3].value)
        related_taxon_latname = self.get_stripped_cell_value(row[4].value)
        related_taxon_author = self.get_stripped_cell_value(row[5].value)
        related_taxon_source = self.get_stripped_cell_value(row[6].value)
        description = self.get_stripped_cell_value(row[7].value)
        
        # skip empty rows
        if not relationship_name and not taxon_latname and not taxon_source and not related_taxon_latname and not related_taxon_source:
            pass
        
        else:
            if relationship_name:
                # check if relationship type exists
                taxon_relationship_type = self.get_taxon_relationship_type_by_name(relationship_name)
                if not taxon_relationship_type:
                    message = _('Relationship Type "%(relationship_name)s" not found.') % {
                        'relationship_name': relationship_name
                    }
                    self.add_cell_error(self.workbook_filename, TAXON_RELATIONSHIPS_SHEET_NAME, 'A', row_index, message)
            else:
                message = _('Relationship is required.')
                self.add_cell_error(self.workbook_filename, TAXON_RELATIONSHIPS_SHEET_NAME, 'A', row_index, message)

            self.validate_taxon(taxon_latname, taxon_author, taxon_source, self.workbook_filename, TAXON_RELATIONSHIPS_SHEET_NAME,
                                        row_index, 2, 3)
            
            self.validate_taxon(related_taxon_latname, related_taxon_author, related_taxon_source, self.workbook_filename, TAXON_RELATIONSHIPS_SHEET_NAME,
                                        row_index, 5, 6)

    # content, not definition rows
    def validate_taxon_relationships_sheet(self):
        
        taxon_relationships_sheet = self.get_sheet_by_name(TAXON_RELATIONSHIPS_SHEET_NAME)
        
        if not taxon_relationships_sheet:
            message = _('Sheet "%(sheet_name)s" not found in the spreadsheet') % {
                'sheet_name': TAXON_RELATIONSHIPS_SHEET_NAME,
            }
            self.errors.append(message)
            
        else:
            for row_index, row in enumerate(taxon_relationships_sheet.iter_rows(min_row=3), 0):
                self.validate_taxon_relationship_row(row, row_index)

    # self.workbook is available
    def validate_spreadsheet(self):
        self.validate_definition_rows()
        self.validate_taxon_relationship_types_sheet()
        self.validate_taxon_relationships_sheet()


    def import_taxon_relationship_types(self):
        
        taxon_relationship_types_sheet = self.get_sheet_by_name(TAXON_RELATIONSHIP_TYPES_SHEET_NAME)
        
        for row in taxon_relationship_types_sheet.iter_rows(min_row=2):
            relationship_name = self.get_stripped_cell_value(row[0].value)
            taxon_role = self.get_stripped_cell_value(row[1].value)
            related_taxon_role = self.get_stripped_cell_value(row[2].value)
            
            
            # skip empty rows
            if not relationship_name and not taxon_role and not related_taxon_role:
                continue
            
            taxon_relationship_type, created = TaxonRelationshipType.objects.get_or_create(
                backbonetaxonomy=self.generic_content,
                relationship_name=relationship_name,
                defaults={
                    'taxon_role': taxon_role,
                    'related_taxon_role': related_taxon_role
                }
            )
            
            if not created:
                taxon_relationship_type.taxon_role = taxon_role
                taxon_relationship_type.related_taxon_role = related_taxon_role
                taxon_relationship_type.save()
    
    def import_taxon_relationships(self):
        
        taxon_relationships_sheet = self.get_sheet_by_name(TAXON_RELATIONSHIPS_SHEET_NAME)
        
        for row in taxon_relationships_sheet.iter_rows(min_row=3):
            
            relationship_name = self.get_stripped_cell_value(row[0].value)
            taxon_latname = self.get_stripped_cell_value(row[1].value)
            taxon_author = self.get_stripped_cell_value(row[2].value)
            taxon_source = self.get_stripped_cell_value(row[3].value)
            related_taxon_latname = self.get_stripped_cell_value(row[4].value)
            related_taxon_author = self.get_stripped_cell_value(row[5].value)
            related_taxon_source = self.get_stripped_cell_value(row[6].value)
            description = self.get_stripped_cell_value(row[7].value)
            
            # skip empty rows
            if not relationship_name and not taxon_latname and not taxon_source and not related_taxon_latname and not related_taxon_source:
                continue
            
            lazy_taxon = self.get_lazy_taxon(taxon_latname, taxon_source, taxon_author=taxon_author)
            related_lazy_taxon = self.get_lazy_taxon(related_taxon_latname, related_taxon_source, taxon_author=related_taxon_author)
            
            taxon_relationship_type = TaxonRelationshipType.objects.get(relationship_name=relationship_name)
            
            taxon_relationship = TaxonRelationship.objects.filter(
                backbonetaxonomy=self.generic_content,
                taxon_source=lazy_taxon.taxon_source,
                name_uuid=lazy_taxon.name_uuid,
                related_taxon_source=related_lazy_taxon.taxon_source,
                related_taxon_name_uuid=related_lazy_taxon.name_uuid,
                relationship_type=taxon_relationship_type
            ).first()
            
            if not taxon_relationship:
                taxon_relationship = TaxonRelationship(
                    backbonetaxonomy=self.generic_content,
                    taxon_source=lazy_taxon.taxon_source,
                    taxon_latname=lazy_taxon.taxon_latname,
                    taxon_author=lazy_taxon.taxon_author,
                    name_uuid=lazy_taxon.name_uuid,
                    taxon_nuid=lazy_taxon.taxon_nuid,
                    related_taxon_source=related_lazy_taxon.taxon_source,
                    related_taxon_latname=related_lazy_taxon.taxon_latname,
                    related_taxon_author=related_lazy_taxon.taxon_author,
                    related_taxon_name_uuid=related_lazy_taxon.name_uuid,
                    related_taxon_nuid=related_lazy_taxon.taxon_nuid,
                    relationship_type=taxon_relationship_type,
                )
            
            taxon_relationship.description = description
            taxon_relationship.save()
        
    def import_generic_content(self):

        if self.is_valid == False:
            raise ValueError('Only valid zipfiles can be imported.')

        self.import_taxon_relationship_types()
        self.import_taxon_relationships()
            


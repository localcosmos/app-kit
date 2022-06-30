from django.conf import settings
from django.utils.translation import gettext_lazy as _

from app_kit.generic_content_zip_import import GenericContentZipImporter

from app_kit.features.taxon_profiles.models import TaxonProfile, TaxonTextType, TaxonText


import os, openpyxl


TAXON_SOURCES = [d[0] for d in settings.TAXONOMY_DATABASES]


'''
    TaxonProfiles as Spreadsheet
    - only reads the first sheet
'''

class TaxonProfilesZipImporter(GenericContentZipImporter):

    required_additional_files = {}


    def validate(self):

        self.errors = []
        self.check_file_presence()

        self.filepath = self.get_filepath(self.generic_content.name, self.spreadsheet_extensions)
        if self.filepath is not None:
            self.workbook = openpyxl.load_workbook(self.filepath)
            self.workbook_filename = os.path.basename(self.filepath)
            self.validate_spreadsheet()

        is_valid = len(self.errors) == 0

        return is_valid
    
    # self.workbook is available
    def validate_spreadsheet(self):

        taxon_profiles_sheet = self.get_sheet_by_index(0)

        for row_index, row in enumerate(taxon_profiles_sheet.iter_rows(), 1):

            if row_index == 1:

                if not row[0].value or row[0].value.lower() != 'scientific name':
                    message = _('Cell content has to be "Scientific name", not {0}'.format(row[0].value))
                    self.add_cell_error(self.workbook_filename, taxon_profiles_sheet.title, 'A', 0, message)

                if not row[1].value or row[1].value.lower() != 'author (optional)':
                    message = _('Cell content has to be "Author (optional)", not {0}'.format(row[1].value))
                    self.add_cell_error(self.workbook_filename, taxon_profiles_sheet.title, 'B', 0, message)

                if not row[2].value or row[2].value.lower() != 'taxonomic source':

                    message = _('Cell content has to be "Taxonomic source", not {0}'.format(row[2].value))
                    self.add_cell_error(self.workbook_filename, taxon_profiles_sheet.title, 'C', 0, message)


            else:

                # skip empty rows
                if not row[0].value:
                    continue

                if not row[2].value:
                    message = _('Cell content has to be a taxonomic source, found empty cell instead')
                    self.add_cell_error(self.workbook_filename, taxon_profiles_sheet.title, 'C', row_index, message)


                if row[0].value and row[2].value:

                    taxon_latname = row[0].value.strip()

                    taxon_author = None
                    if row[1].value:
                        taxon_author = row[1].value.strip()
                    taxon_source = row[2].value.strip()

                    self.validate_taxon(taxon_latname, taxon_author, taxon_source, self.workbook_filename,
                                        taxon_profiles_sheet.title, row_index, 0, 2)

 

    def valdiate_images(self):
        pass
        

    def import_generic_content(self):

        if len(self.errors) != 0:
            raise ValueError('Only valid zipfiles can be imported.')

        # first, delete removed text_types and add new text_types
        # try to preserve taxon texts
        existing_text_types = list(TaxonTextType.objects.filter(taxon_profiles=self.generic_content).values_list(
            'text_type', flat=True))

        new_text_types = []
        

        # import from spreadsheet
        taxon_profiles_sheet = self.get_sheet_by_index(0)

        # a list of text_type instances
        text_types = []

        # read the file row-by-row
        for row_index, row in enumerate(taxon_profiles_sheet.iter_rows(), 1):

            if not row[0].value:
                continue

            # the second row is the first row with taxon and text
            # first, get the lazy_taxon and the TaxonProfile
            if row_index > 1:

                taxon_latname = row[0].value
                taxon_author = row[1].value
                taxon_source = row[2].value

                lazy_taxon = self.get_lazy_taxon(taxon_latname, taxon_source, taxon_author=taxon_author)

                taxon_profile = TaxonProfile.objects.filter(taxon_profiles=self.generic_content,
                        taxon_latname=lazy_taxon.taxon_latname, taxon_author=lazy_taxon.taxon_author).first()

                if not taxon_profile:
                    taxon_profile = TaxonProfile(
                        taxon_profiles=self.generic_content,
                        taxon=lazy_taxon,
                    )

                    taxon_profile.save()

                
            # iterate over all columns of the current row
            for column_index, cell in enumerate(row, 0):

                cell = row[column_index]

                # value can be a taxon text content (row #2+) or a taxon text definition (only row #1)
                value = cell.value

                if value and len(value) > 0:

                    # the first row defines text types
                    if row_index == 1:

                        text_type_name = value
                        
                        # skip the first 3 cells (Scientific name, Author, Taxonomic Source)
                        if column_index >= 3:

                            position = column_index - 1

                            if text_type_name in existing_text_types:
                                existing_text_types.pop(existing_text_types.index(text_type_name))

                                text_type = TaxonTextType.objects.get(
                                    taxon_profiles = self.generic_content,
                                    text_type = text_type_name,
                                )

                                text_type.position = position
                                text_type.save()

                            else:
                                # create a text_type
                                text_type = TaxonTextType(
                                    taxon_profiles = self.generic_content,
                                    text_type = text_type_name,
                                    position = position,
                                )

                                text_type.save()

                            text_types.append(text_type)

                    # all rows beginning with row #2 define taxon texts
                    else:

                        taxon_text_content = value
                        # column indexes 0, 1 and 2 define the taxon, index 3 onward is taxon text content
                        # column 0(scientific name), 1 (author), 2 (source) + len(text_types) =number of columns
                        max_column_index_with_content = len(text_types) + 3
                        
                        if column_index > 2 and column_index <= max_column_index_with_content:

                            # column_index is the column index in the spreadsheet, which is 3 more than
                            # the index in the list text_types[]
                            text_type = text_types[column_index - 3]

                            # try to preserve translations
                            taxon_text = TaxonText.objects.filter(taxon_profile=taxon_profile,
                                                                  taxon_text_type=text_type).first()

                            if not taxon_text:
                                taxon_text = TaxonText(
                                    taxon_profile=taxon_profile,
                                    taxon_text_type=text_type,
                                )

                            taxon_text.text = taxon_text_content
                            taxon_text.position = text_type.position

                            taxon_text.save()

        # delete removed text_types
        remaining_text_types = TaxonTextType.objects.filter(taxon_profiles=self.generic_content,
                                                            text_type__in=existing_text_types)

        remaining_text_types.delete()
                        
                    
                    

                


        

    

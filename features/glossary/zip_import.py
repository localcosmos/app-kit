from django.conf import settings
from django.utils.translation import gettext_lazy as _

from app_kit.generic_content_zip_import import GenericContentZipImporter

from app_kit.features.glossary.models import GlossaryEntry, TermSynonym


import os, openpyxl


'''
    Glossary as Spreadsheet
    - only reads the first sheet
'''

class GlossaryZipImporter(GenericContentZipImporter):

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

        glossary_sheet = self.get_sheet_by_index(0)
        found_synonyms = {}

        for row_index, row in enumerate(glossary_sheet.iter_rows(), 1):

            if row_index == 0:

                if row[0].value.lower() != 'term':
                    message = _('Cell content has to be "Term", not {0}'.format(row[0].value))
                    self.add_cell_error(self.workbook_filename, glossary_sheet.title, 1, 0, message)


                if row[1].value.lower() != 'synonyms':

                    message = _('Cell content has to be "Synonyms", not {0}'.format(row[1].value))
                    self.add_cell_error(self.workbook_filename, glossary_sheet.title, 1, 0, message)
                    

                if row[2].value.lower() != 'definition':

                    message = _('Cell content has to be "Definition", not {0}'.format(row[2].value))
                    self.add_cell_error(self.workbook_filename, glossary_sheet.title, 1, 0, message)


            else:

                term = row[0].value
                synonyms = row[1].value
                definition = row[2].value

                self.validate_glossary_entry(term, synonyms, definition, glossary_sheet.title, row_index)

                if synonyms:
                    synonyms_list = synonyms.split('|')
                    synonyms_list = [s.strip() for s in synonyms_list]
                    
                    for synonym in synonyms_list:
                        if synonym not in found_synonyms:
                            found_synonyms[synonym] = term

                        else:
                            if found_synonyms[synonym] != term:
                                message = _('Unambiguous synonym: {0} is mapped to {1} and {2}'.format(
                                    synonym, term, found_synonyms[synonym]))
                                            
                                self.add_cell_error(self.workbook_filename, glossary_sheet.title, 1, 0, message)
                            

    def validate_glossary_entry(self, term, synonyms, definition, glossary_sheet_name, row_index):

        if not term:
            message = _('No term found.')
            self.add_cell_error(self.workbook_filename, glossary_sheet_name, 0, row_index, message)
            
        if not definition:
            message = _('No definition found.')
            self.add_cell_error(self.workbook_filename, glossary_sheet_name, 1, row_index, message)
            


    def valdiate_images(self):
        pass
        

    def import_generic_content(self):

        if len(self.errors) != 0:
            raise ValueError('Only valid zipfiles can be imported.')

        glossary_sheet = self.get_sheet_by_index(0)

        # check if the term exists - only update its synonyms and definition if it is new
        db_glossary_entries = GlossaryEntry.objects.filter(glossary=self.generic_content)
        delete_glossary_entries = [e.term for e in db_glossary_entries]
                        
        for row_index, row in enumerate(glossary_sheet.iter_rows(), 1):

            if row_index == 0:
                continue

            save_entry = False
            created = False

            term = row[0].value

            synonyms = []
            synonyms_value = row[1].value
            
            if synonyms_value:
                synonyms = [s.strip() for s in synonyms_value.split('|')]

            definition = row[2].value

            
            db_glossary_entry = GlossaryEntry.objects.filter(glossary=self.generic_content, term=term).first()

            if db_glossary_entry:
                # exists in db and excel, do not delete this glossary entry
                del delete_glossary_entries[delete_glossary_entries.index(db_glossary_entry.term)]
                
            else:
                iexact_qry = GlossaryEntry.objects.filter(glossary=self.generic_content, term__iexact=term)

                if iexact_qry.count() == 1:
                    db_glossary_entry = iexact_qry.first()                    

                    # exists in db and excel, do not delete this glossary entry
                    del delete_glossary_entries[delete_glossary_entries.index(db_glossary_entry.term)]
                    
                else:

                    # new entry
                    db_glossary_entry = GlossaryEntry(
                        glossary=self.generic_content,
                        term=term,
                    )

                    created = True
                    save_entry = True


            # db_glossary_entry is now present

            # check if case has been altered, eg. TErm -> Term
            if db_glossary_entry.term != term:
                
                db_glossary_entry.term = term
                save_entry = True
                
            # check if definition has been altered
            if db_glossary_entry.definition != definition:

                db_glossary_entry.definition = definition
                save_entry = True


            if save_entry == True:
                db_glossary_entry.save()



            # add or delete synonyms
            existing_synonyms = TermSynonym.objects.filter(glossary_entry__glossary=self.generic_content,
                                                           glossary_entry=db_glossary_entry)
            
            delete_synonyms = [s.term for s in existing_synonyms]

            for synonym in synonyms:

                db_synonym = TermSynonym.objects.filter(glossary_entry=db_glossary_entry,
                                                        term=synonym).first()

                if db_synonym:
                    if db_synonym.term in delete_synonyms:
                        del delete_synonyms[delete_synonyms.index(db_synonym.term)]
                    
                else:
                    # iexact query
                    db_synonym = TermSynonym.objects.filter(glossary_entry__glossary=self.generic_content,
                                                            term__iexact=synonym).first()

                    # correct case, eg TErm -> Term
                    if db_synonym:

                        if db_synonym.glossary_entry != db_glossary_entry:
                            db_synonym.glossary_entry = db_glossary_entry
                            
                        db_synonym.term = synonym
                        db_synonym.save()

                        # exists in db and in excel, do not delete
                        if db_synonym.term in delete_synonyms:
                            del delete_synonyms[delete_synonyms.index(db_synonym.term)]

                    else:
                        # synonym not in db, create
                        db_synonym = TermSynonym(
                            glossary_entry=db_glossary_entry,
                            term=synonym,
                        )

                        db_synonym.save()

            if delete_synonyms:
                db_synonyms = TermSynonym.objects.filter(glossary_entry=db_glossary_entry,
                                                         term__in=delete_synonyms)

                db_synonyms.delete()


        # delete all entries that are present in the db, but not in excel
        if delete_glossary_entries:
            entries = GlossaryEntry.objects.filter(glossary=self.generic_content,
                                                   term__in=delete_glossary_entries)
            entries.delete()
            


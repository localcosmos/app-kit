from django.conf import settings
from django.core.files import File
from django.contrib.contenttypes.models import ContentType

from django.utils.translation import gettext_lazy as _
from app_kit.models import ImageStore, ContentImage

from content_licencing.models import ContentLicenceRegistry
from content_licencing.licences import ContentLicence
from content_licencing import settings as content_licencing_settings

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon
TAXON_SOURCES = [d[0] for d in settings.TAXONOMY_DATABASES]

import os, string, openpyxl, hashlib, json

from PIL import Image

LICENCES_SHORT = [l['short_name'] for l in content_licencing_settings.CONTENT_LICENCING_LICENCES]

'''
openpyxl data_types
TYPE_STRING = 's'
TYPE_FORMULA = 'f'
TYPE_NUMERIC = 'n'
TYPE_BOOL = 'b'
TYPE_NULL = 'n'
TYPE_INLINE = 'inlineStr'
TYPE_ERROR = 'e'
TYPE_FORMULA_CACHE_STRING = 'str'
'''

class GenericContentZipImporter:

    required_additional_files = {
        'Image_Licences' : ['xls', 'xlsx'],
    }
    
    spreadsheet_extensions = ['xls', 'xlsx']

    image_folder_name = 'images'
    image_file_extensions = ['png', 'jpg', 'jpeg']


    def __init__(self, user, generic_content, zip_contents_path):

        self.user = user

        self.generic_content = generic_content
        self.zip_contents_path = zip_contents_path

        self.image_folder = os.path.join(zip_contents_path, self.image_folder_name)


    def validate(self):

        self.errors = []

        self.check_file_presence()
        self.validate_spreadsheet()
        self.validate_image_licences()
        self.validate_images()

        is_valid = len(self.errors) == 0

        return is_valid


    def get_filepath(self, filename, allowed_extensions):

        allowed_filenames = []

        for extension in allowed_extensions:

            full_filename = '{0}.{1}'.format(filename, extension)
            allowed_filenames.append(full_filename)

            filepath = os.path.join(self.zip_contents_path, full_filename)

            if os.path.isfile(filepath):
                return filepath

        return None
            

    def check_file_presence(self):

        # there has to be .xls or .xlsx or odt file by the name of the generic_content
        spreadsheet_filenames = []
        
        for spreadsheet_extension in self.spreadsheet_extensions:
            spreadsheet_filenames.append('{0}.{1}'.format(self.generic_content.name, spreadsheet_extension))


        spreadsheet_found = False

        for spreadsheet_filename in spreadsheet_filenames:

            spreadsheet_path = os.path.join(self.zip_contents_path, spreadsheet_filename)

            if os.path.isfile(spreadsheet_path):
                spreadsheet_found = True
                break

        if spreadsheet_found == False:
            allowed_spreadsheet_files = ', '.join(spreadsheet_filenames)
            self.errors.append(_('Missing spreadsheet file. Expected one of these files: %(files)s') % {
                'files': allowed_spreadsheet_files,
            })


        for filename, extensionlist in self.required_additional_files.items():

            file_found = False

            allowed_files = []

            for extension in extensionlist:

                full_filename = '{0}.{1}'.format(filename, extension)

                allowed_files.append(full_filename)

                filepath = os.path.join(self.zip_contents_path, full_filename)

                if os.path.isfile(filepath):
                    file_found = True
                    break

            if file_found == False:
                self.errors.append(_('Missing additional file. Allowed files: %(files)s') % {'files': allowed_files} )


    def get_image_licences_workbook(self):

        licence_workbook = None
        workbook_filename = None
        
        for extension in self.required_additional_files['Image_Licences']:
            filename = 'Image_Licences.{0}'.format(extension)

            filepath = os.path.join(self.zip_contents_path, filename)

            if os.path.isfile(filepath):
                licence_workbook = openpyxl.load_workbook(filepath)
                workbook_filename = filename


        return licence_workbook, workbook_filename


    def get_sheet_by_index(self, index):
        sheet_names = self.workbook.sheetnames

        sheet = self.workbook[sheet_names[0]]

        return sheet


    # get a sheet by name
    def get_sheet_by_name(self, sheet_name):

        sheet_names = self.workbook.sheetnames

        if not sheet_name in sheet_names:

            self.errors.append(_('Sheet "%(sheet_name)s" not found in %(filename)s') % {
                    'filename' : self.workbook_filename,
                    'sheet_name' : sheet_name,
                })

            return None

        sheet = self.workbook[sheet_name]

        return sheet



    def get_optional_sheet_by_name(self, sheet_name):
        workbook = openpyxl.load_workbook(self.filepath)

        if sheet_name in workbook.sheetnames:
            return workbook[sheet_name]

        return None


    def import_generic_content(self):
        raise NotImplementedError('GenericContentZipValidator classes require a import_generic_content method')

    def validate_spreadsheet(self):
        raise NotImplementedError('GenericContentZipValidator classes require a validate_spreadsheet method')

    def validate_images(self):
        raise NotImplementedError('GenericContentZipValidator classes require a validate_images method')

    # validate all image licences
    def validate_image_licences(self):

        licence_workbook, workbook_filename = self.get_image_licences_workbook()

        if licence_workbook is not None:

            licence_sheet = licence_workbook[licence_workbook.sheetnames[0]]
            licences = {}


            for row_index, row in enumerate(licence_sheet.iter_rows(), 1):

                if row_index == 0:
                    continue


                licences[row[0].value.lower()] = {
                    'row' : row,
                    'row_index' : row_index,
                }

            # iterate over all images and check if there is a correct licence entry
            for root, dirs, files in os.walk(self.image_folder):

                for file in files:

                    abspath = os.path.join(root, file)

                    # case insensitive lookup
                    relpath = os.path.relpath(abspath, self.image_folder)
                    relpath_lower = relpath.lower()

                    # relpath has to be in image licences
                    if relpath_lower not in licences:
                        message = _('[%(licence_file)s] No image licence found for: "%(image_path)s"' % {
                            'licence_file' : workbook_filename,
                            'image_path' : relpath,
                        })

                        self.errors.append(message)

                    else:

                        licence_dic = licences[relpath_lower]
                        licence = licence_dic['row']

                        # some licences require a link to the creator. Creator Name is required
                        licence_short = licence[1].value


                        if not licence_short:
                            message = _('No image licence found')

                            self.add_cell_error(workbook_filename, licence_sheet.name, 1, licence_dic['row_index'],
                                                message)

                        elif licence_short not in LICENCES_SHORT:
                            message = _('Invalid licence: %(licence)s' % {
                                'licence': licence_short,
                            })
                            self.add_cell_error(workbook_filename, licence_sheet.name, 1, licence_dic['row_index'],
                                                message)

                        creator_name = licence[2].value

                        if not creator_name:

                            message = _('Creator name is missing')
                            self.add_cell_error(workbook_filename, licence_sheet.name, 2, licence_dic['row_index'],
                                                message)
                        


    def add_cell_error(self, filename, sheet_name, column, row, message):

        error_message = _('[%(filename)s][Sheet:%(sheet_name)s][cell:%(column)s%(row)s] %(message)s' % {
            'filename' : filename,
            'sheet_name' : sheet_name,
            'row' : row + 1,
            'column' : column,
            'message' : message,
        })

        self.errors.append(error_message)
        

    def add_row_error(self, filename, sheet_name, row, message):

        error_message = _('[%(filename)s][Sheet:%(sheet_name)s][row: %(row)s] %(message)s' % {
            'filename' : filename,
            'sheet_name' : sheet_name,
            'row' : row + 1,
            'message' : message,
        })

        self.errors.append(error_message)


    def save_content_image(self, image_filepath, content_object, image_licence_path):
        #print('image found: {0}'.format(image_filepath))

        content_type = ContentType.objects.get_for_model(content_object)
        object_id = content_object.id

        image_file = File(open(image_filepath, 'rb'))

        md5 = hashlib.md5(image_file.read()).hexdigest()

        crop_parameters = self.get_crop_parameters(image_filepath)

        image_store = ImageStore(
            source_image=image_file,
            md5=md5,
            uploaded_by=self.user,
        )

        image_store.save()

        content_image = ContentImage(
            image_store=image_store,
            crop_parameters=json.dumps(crop_parameters),
            content_type = content_type,
            object_id = object_id,
        )

        content_image.save()

        self.register_content_licence(image_store, 'source_image', image_licence_path)


    def get_crop_parameters(self, image_filepath):

        im = Image.open(image_filepath)
        width, height = im.size

        #"{"x":0,"y":0,"width":1000,"height":1000,"rotate":0}"
        crop_parameters = {
            'x' : 0,
            'y': 0,
            'width' : width,
            'height' : height,
            'rotate' : 0,
        }

        return crop_parameters


    def get_licence_from_path(self, image_licence_path):

        licence_workbook, workbook_filename = self.get_image_licences_workbook()
        licence_sheet = licence_workbook[licence_workbook.sheetnames[0]]

        licence_definition = None
        
        for row in licence_sheet.iter_rows():
            
            if row[0].value == image_licence_path:
                
                licence_definition = {
                    'short_name' : row[1].value,
                    'creator_name' : row[2].value,
                    'creator_link' : row[3].value,
                }

                break

        return licence_definition

        
    # image_licence_path is the entry in the 'Image' column of ImageLicences.xls(x)
    def register_content_licence(self, instance, model_field, image_licence_path):
        # register content licence

        licence_definition = self.get_licence_from_path(image_licence_path)

        if licence_definition:

            licence = ContentLicence(licence_definition['short_name'])

            licence_kwargs = {
                'creator_name' : licence_definition['creator_name'],
                'creator_link' : licence_definition['creator_link'],
            }
        
            registry_entry = ContentLicenceRegistry.objects.register(instance, model_field, self.user,
                            licence.short_name, licence.version, **licence_kwargs)


    def validate_taxon(self, taxon_latname, taxon_author, taxon_source, workbook_filename, sheet_name,
                       row_number, taxon_latname_column_index, taxon_source_column_index):

        if taxon_source in TAXON_SOURCES:

            # check if the taxon exists
            models = TaxonomyModelRouter(taxon_source)

            search_kwargs = {
                'taxon_latname' : taxon_latname
            }

            if taxon_author:
                search_kwargs['taxon_author'] = taxon_author

            taxon_count = models.TaxonTreeModel.objects.filter(**search_kwargs).count()
            
            if taxon_count == 0:
                if taxon_author:
                    message = _('%(taxon_latname)s %(taxon_author)s not found in %(taxon_source)s' % {
                        'taxon_latname' : taxon_latname,
                        'taxon_author' : taxon_author,
                        'taxon_source' : taxon_source,
                    })

                else:
                    message = _('%(taxon_latname)s not found in %(taxon_source)s' % {
                        'taxon_latname' : taxon_latname,
                        'taxon_source' : taxon_source,
                    })
                    

                self.add_row_error(workbook_filename, sheet_name, row_number, message)

            elif taxon_count > 1:

                if taxon_author:
                    message = _('Multiple results found for %(taxon_latname)s %(taxon_author)s in %(taxon_source)s' % {
                        'taxon_latname' : taxon_latname,
                        'taxon_author' : taxon_author,
                        'taxon_source': taxon_source,
                    })

                else:
                    message = _('Multiple results found for %(taxon_latname)s in %(taxon_source)s' % {
                        'taxon_latname' : taxon_latname,
                        'taxon_source': taxon_source,
                    })

                self.add_row_error(workbook_filename, sheet_name, row_number, message)

        else:
            message = _('Invalid taxonomic source: %(taxon_source)s' % {
                'taxon_source' : taxon_source,
            })

            self.add_cell_error(workbook_filename, sheet_name, taxon_source_column_index, row_number, message)


    def get_lazy_taxon(self, taxon_latname, taxon_source, taxon_author=None):

        models = TaxonomyModelRouter(taxon_source)

        field_kwargs = {
            'taxon_latname' : taxon_latname,
        }

        if taxon_author:
            field_kwargs['taxon_author'] = taxon_author

        taxon = models.TaxonTreeModel.objects.get(**field_kwargs)

        lazy_taxon = LazyTaxon(instance=taxon)
        return lazy_taxon
        




        
    

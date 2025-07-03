from django.conf import settings
from django.core.files import File
from django.contrib.contenttypes.models import ContentType

from django.utils.translation import gettext_lazy as _
from app_kit.models import ImageStore, ContentImage

from localcosmos_server.utils import generate_md5

from content_licencing.models import ContentLicenceRegistry
from content_licencing.licences import ContentLicence, LICENCE_LOOKUP
from content_licencing import settings as content_licencing_settings


from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon
TAXON_SOURCES = [d[0] for d in settings.TAXONOMY_DATABASES]

import os, openpyxl, json, re

from PIL import Image

LICENCES_SHORT = [l['short_name'] for l in content_licencing_settings.CONTENT_LICENCING_LICENCES]
VALID_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
IMAGE_MAX_WIDTH = 2000
IMAGE_MAX_HEIGHT = 2000

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
    
    spreadsheet_extensions = ['xlsx',]

    image_folder_name = 'images'
    image_file_extensions = ['png', 'jpg', 'jpeg', 'webp']
    
    images_sheet_name = 'Images'


    def __init__(self, user, generic_content, zip_contents_path, ignore_nonexistent_images=False):

        self.user = user

        self.generic_content = generic_content
        self.zip_contents_path = zip_contents_path

        self.image_folder = os.path.join(zip_contents_path, self.image_folder_name)
        
        self.ignore_nonexistent_images = ignore_nonexistent_images
        
        self.is_valid = False
        
    
    def import_generic_content(self):
        raise NotImplementedError('GenericContentZipValidator classes require a import_generic_content method')

    def validate_spreadsheet(self):
        raise NotImplementedError('GenericContentZipValidator classes require a validate_spreadsheet method')
        
    
    def load_workbook(self):
        
        filepath = self.get_filepath(self.generic_content.name, self.spreadsheet_extensions)
        if filepath is None:
            raise ValueError('No spreadsheet file found')
        self.workbook = openpyxl.load_workbook(filepath)
        self.workbook_filename = os.path.basename(filepath)
        
        
    def get_stripped_cell_value(self, cell_value):
        if cell_value:
            cell_value = cell_value.strip()
        else:
            cell_value = None
        return cell_value
    
    def get_stripped_cell_value_lowercase(self, cell_value):
        if cell_value:
            cell_value = cell_value.strip().lower()
        else:
            cell_value = None
        return cell_value


    def validate(self):
        
        self.errors = []

        self.check_file_presence()
        
        if not self.errors:
            self.load_workbook()
            self.validate_spreadsheet()
            self.validate_images_sheet()

        self.is_valid = len(self.errors) == 0

        return self.is_valid


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

    # get a sheet by name
    def get_sheet_by_name(self, sheet_name):

        sheet_names = self.workbook.sheetnames

        if not sheet_name in sheet_names:
            return None

        sheet = self.workbook[sheet_name]

        return sheet


    def get_optional_sheet_by_name(self, sheet_name):
        workbook = openpyxl.load_workbook(self.filepath)

        if sheet_name in workbook.sheetnames:
            return workbook[sheet_name]

        return None
    
    
    def get_image_data_from_images_sheet(self, image_filename):
        images_sheet = self.get_sheet_by_name(self.images_sheet_name)
        image_data = None
        
        for row in images_sheet.iter_rows(min_row=2):

            if row[0].value == image_filename:
                image_data = {
                    'identifier': self.get_stripped_cell_value(row[0].value),
                    'author': self.get_stripped_cell_value(row[1].value),
                    'licence': self.get_stripped_cell_value(row[2].value),
                    'licence_version': self.get_stripped_cell_value(row[3].value),
                    'link_to_source_image': self.get_stripped_cell_value(row[4].value),
                    'title': self.get_stripped_cell_value(row[5].value),
                    'caption': self.get_stripped_cell_value(row[6].value),
                    'alt_text': self.get_stripped_cell_value(row[7].value),
                    'primary_image': self.get_stripped_cell_value(row[8].value),
                }
                break
        
        return image_data
    

    def validate_listing_in_images_sheet(self, image_filename, col_letter, row_index):
        
        image_data = self.get_image_data_from_images_sheet(image_filename)
        
        if not image_data and self.ignore_nonexistent_images == False:
            message = _('Image file "%(image_filename)s" not found in the "%(images_sheet_name)s" sheet.') % {
                'image_filename': image_filename,
                'images_sheet_name': self.images_sheet_name,
            }
            self.add_cell_error(self.workbook_filename, self.generic_content.name, col_letter, row_index, message)
            
    def get_image_file_disk_path(self, image_filename):
        # check if the image exists in the unzipped folder
        images_folder = os.path.join(self.zip_contents_path, self.image_folder_name)
        image_path = os.path.join(images_folder, image_filename)

        return image_path
    
    def validate_image_data(self, image_data, sheet_name, row_index):
        
        if not image_data['author']:
            message = _('Cell content has to be an author, found empty cell instead')
            self.add_cell_error(self.workbook_filename, sheet_name, 'B', row_index, message)
            
        if image_data['licence'] not in LICENCE_LOOKUP:
            message = _('Invalid licence: %(cell_value)s. Licence choices are: %(licence_choices)s') % {
                'cell_value': image_data['licence'],
                'licence_choices': ', '.join(LICENCE_LOOKUP.keys()),
            }
            self.add_cell_error(self.workbook_filename, sheet_name, 'C', row_index, message)
        
        if image_data['licence'] in LICENCE_LOOKUP and image_data['licence_version'] not in LICENCE_LOOKUP[image_data['licence']]:
            message = _('Invalid licence version: %(cell_value)s. Licence version choices are: %(licence_choices)s') % {
                'cell_value': image_data['licence_version'],
                'licence_choices': ', '.join(LICENCE_LOOKUP[image_data['licence']].keys()),
            }
            self.add_cell_error(self.workbook_filename, sheet_name, 'D', row_index, message)
            
            
        # check if the image exists in the unzipped folder and if it meets the pixel sizes etc
        # check if the image is a valid image format
        image_filename = image_data['identifier']
        
        image_extension = os.path.splitext(image_filename)[1].lower()
        if image_extension not in VALID_IMAGE_FORMATS:
            message = _('Invalid image format: %(cell_value)s. Valid formats are: %(valid_formats)s') % {
                'cell_value': image_extension,
                'valid_formats': ', '.join(VALID_IMAGE_FORMATS),
            }
            self.add_cell_error(self.workbook_filename, sheet_name, 'A', row_index, message)
            
        # check if the image exists in the unzipped folder
        image_path = self.get_image_file_disk_path(image_filename)
        if os.path.exists(image_path):
            # check if the image is square
            self.validate_square_image(image_path)
                
        else:
            if self.ignore_nonexistent_images == False:
                message = _('Image file not found: %(cell_value)s. Image file should be in the images folder.') % {
                    'cell_value': image_filename,
                }
                self.add_cell_error(self.workbook_filename, sheet_name, 'A', row_index, message)
            
            
            
    def validate_images_sheet(self):
        
        images_sheet = self.get_sheet_by_name(self.images_sheet_name)
        
        if images_sheet:
        
            for row_index, row in enumerate(images_sheet.iter_rows(), 0):
                
                if row_index == 0:
                    if not row[0].value or row[0].value.lower() != 'identifier':
                        
                        message = _('Cell content has to be "Identifier", not %(cell_value)s') % {
                            'cell_value': row[0].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'A', 0, message)
                        
                    if not row[1].value or row[1].value.lower() != 'author':
                        message = _('Cell content has to be "Author", not %(cell_value)s') % {
                            'cell_value': row[1].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'B', 0, message)
                    if not row[2].value or row[2].value.lower() != 'licence':
                        message = _('Cell content has to be "Licence", not %(cell_value)s') % {
                            'cell_value': row[2].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'C', 0, message)
                    if not row[3].value or row[3].value.lower() != 'licence version':
                        message = _('Cell content has to be "Licence version", not %(cell_value)s') % {
                            'cell_value': row[3].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'D', 0, message)
                    if not row[4].value or row[4].value.lower() != 'link to source image (optional)':
                        message = _('Cell content has to be "Link to source image (optional)", not %(cell_value)s') % {
                            'cell_value': row[4].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'E', 0, message)
                    if not row[5].value or row[5].value.lower() != 'title (optional)':
                        message = _('Cell content has to be "Title (optional)", not %(cell_value)s') % {
                            'cell_value': row[5].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'F', 0, message)
                    if not row[6].value or row[6].value.lower() != 'caption (optional)':
                        message = _('Cell content has to be "Caption (optional)", not %(cell_value)s') % {
                            'cell_value': row[6].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'G', 0, message)
                    if not row[7].value or row[7].value.lower() != 'alt text (optional)':
                        message = _('Cell content has to be "Alt text (optional)", not %(cell_value)s') % {
                            'cell_value': row[7].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'H', 0, message)
                    if not row[8].value or row[8].value.lower() != 'primary image (optional)':
                        message = _('Cell content has to be "Primary image (optional)", not %(cell_value)s') % {
                            'cell_value': row[8].value,
                        }
                        self.add_cell_error(self.workbook_filename, images_sheet.title, 'I', 0, message)
            
                else:
                    if not row[0].value:
                        continue
                    
                    image_data = {
                        'identifier': self.get_stripped_cell_value(row[0].value),
                        'author': self.get_stripped_cell_value(row[1].value),
                        'licence': self.get_stripped_cell_value(row[2].value),
                        'licence_version': self.get_stripped_cell_value(row[3].value),
                        'link_to_source_image': self.get_stripped_cell_value(row[4].value),
                        'title': self.get_stripped_cell_value(row[5].value),
                        'caption': self.get_stripped_cell_value(row[6].value),
                        'alt_text': self.get_stripped_cell_value(row[7].value),
                        'primary_image': self.get_stripped_cell_value(row[8].value),
                    }
                    
                    self.validate_image_data(image_data, images_sheet.title, row_index)
                            


    def add_cell_error(self, filename, sheet_name, column, row, message):
        
        if isinstance(column, int):
            column = openpyxl.utils.get_column_letter(column)

        error_message = _('[%(filename)s][Sheet:%(sheet_name)s][cell:%(column)s%(row)s] %(message)s' % {
            'filename' : filename,
            'sheet_name' : sheet_name,
            'row' : row + 1,
            'column' : column,
            'message' : message,
        })

        self.errors.append(error_message)
        

    def add_row_error(self, filename, sheet_name, row, message):

        error_message = _('[%(filename)s][Sheet:%(sheet_name)s][row:%(row)s] %(message)s' % {
            'filename' : filename,
            'sheet_name' : sheet_name,
            'row' : row + 1,
            'message' : message,
        })

        self.errors.append(error_message)



    def get_existing_image_store(self, image_filepath, content_object):
        
        existing_image = None
        with open(image_filepath, 'rb') as image_file:
            new_image_md5 = generate_md5(image_file)
        
        return ImageStore.objects.filter(md5=new_image_md5).first()
        
    def save_content_image(self, image_filepath, content_object, image_data):
        
        image_store = self.get_existing_image_store(image_filepath, content_object)
        
        content_type = ContentType.objects.get_for_model(content_object)
        object_id = content_object.id
        
        if not image_store:
            
            image_file = File(open(image_filepath, 'rb'))

            md5 = generate_md5(image_file)

            image_store = ImageStore(
                source_image=image_file,
                md5=md5,
                uploaded_by=self.user,
            )

            image_store.save()
            image_file.close()
            
        content_image = ContentImage.objects.filter(
            image_store=image_store,
            content_type=content_type,
            object_id=object_id,
        ).first()
        
        if not content_image:
            
            crop_parameters = self.get_crop_parameters(image_filepath)
            
            content_image = ContentImage(
            image_store=image_store,
            crop_parameters=json.dumps(crop_parameters),
            content_type = content_type,
            object_id = object_id
        )        
        
        if image_data['title']:
            content_image.title = image_data['title']
        if image_data['caption']:
            content_image.text = image_data['caption']
        if image_data['alt_text']:
            content_image.alt_text = image_data['alt_text']
        if image_data['primary_image']:
            content_image.is_primary = True

        content_image.save()
        
        image_licence = {
            'short_name' : image_data['licence'],
            'version' : image_data['licence_version'],
            'creator_name' : image_data['author'],
            'source_link' : image_data['link_to_source_image'],
        }

        self.register_content_licence(image_store, 'source_image', image_licence)


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

        
    # image_licence_path is the entry in the 'Image' column of ImageLicences.xls(x)
    def register_content_licence(self, instance, model_field, image_licence):

        licence = ContentLicence(image_licence['short_name'], version=image_licence['version'])

        licence_kwargs = {
            'creator_name' : image_licence['creator_name'],
            'creator_link' : image_licence.get('creator_link', None),
            'source_link' : image_licence.get('source_link', None),
        }
    
        registry_entry = ContentLicenceRegistry.objects.register(instance, model_field, self.user,
                        licence.short_name, licence.version, **licence_kwargs)


    # the taxon validation allows a difference in the taxon author of one space
    def get_taxa_with_taxon_author_tolerance(self, taxon_source, taxon_latname, taxon_author):
        """
        This method checks if the taxon author is valid by allowing a difference of one space.
        It returns a list of valid candidates.
        """
        def is_one_space_difference(a, b):
            # a and b are already stripped
            if abs(len(a) - len(b)) != 1:
                return False
            # Ensure a is the longer string
            if len(b) > len(a):
                a, b = b, a
            for i in range(len(b)):
                if a[i] != b[i]:
                    # Check if the difference is a space in the longer string
                    return a[:i] + a[i+1:] == b and a[i] == ' '
            # Check for extra space at the end
            return a[:-1] == b and a[-1] == ' '
        
        def is_up_to_two_space_differences(a, b):
            # a and b are already stripped
            i, j = 0, 0
            differences = 0
            while i < len(a) and j < len(b):
                if a[i] == b[j]:
                    i += 1
                    j += 1
                elif a[i] == ' ':
                    differences += 1
                    i += 1
                elif b[j] == ' ':
                    differences += 1
                    j += 1
                else:
                    # Not a space difference
                    return False
                if differences > 2:
                    return False
            # Count remaining spaces at the end
            differences += a[i:].count(' ') + b[j:].count(' ')
            return differences <= 2

        matches = []
        models = TaxonomyModelRouter(taxon_source)
        queryset = models.TaxonTreeModel.objects.filter(taxon_latname=taxon_latname)
        input_stripped = taxon_author.strip() if taxon_author else ''

        for taxon in queryset:
            if taxon.taxon_author:
                db_stripped = taxon.taxon_author.strip()
                if db_stripped == input_stripped:
                    matches.append(taxon)
                elif is_up_to_two_space_differences(db_stripped, input_stripped):
                    matches.append(taxon)
        return matches
    
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
                    
                    # check if the taxon author is valid by allowing a difference of one space
                    matches_with_tolerance = self.get_taxa_with_taxon_author_tolerance(taxon_source, taxon_latname, taxon_author)
                    
                    if len(matches_with_tolerance) == 0:
                    
                        message = _('%(taxon_latname)s %(taxon_author)s not found in %(taxon_source)s. Tolerance of two space characters was applied.' % {
                            'taxon_latname' : taxon_latname,
                            'taxon_author' : taxon_author,
                            'taxon_source' : taxon_source,
                        })
                        
                        self.add_row_error(workbook_filename, sheet_name, row_number, message)
                    
                    elif len(matches_with_tolerance) > 1:
                        message = _('Multiple results found for %(taxon_latname)s %(taxon_author)s in %(taxon_source)s. Tolerance of two space characters was applied.' % {
                            'taxon_latname' : taxon_latname,
                            'taxon_author' : taxon_author,
                            'taxon_source': taxon_source,
                        })

                        self.add_row_error(workbook_filename, sheet_name, row_number, message)
                    

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
                    message = _('Multiple results found for %(taxon_latname)s in %(taxon_source)s. You have to specify an author.' % {
                        'taxon_latname' : taxon_latname,
                        'taxon_source': taxon_source,
                    })

                self.add_row_error(workbook_filename, sheet_name, row_number, message)

        else:
            message = _('Invalid taxonomic source: %(taxon_source)s' % {
                'taxon_source' : taxon_source,
            })

            self.add_cell_error(workbook_filename, sheet_name, taxon_source_column_index, row_number, message)



    def get_lazy_taxon_with_tolerance(self, taxon_latname, taxon_source, taxon_author=None):
        """
        This method retrieves a taxon from the database, allowing for a difference of one space in the taxon author.
        It returns a LazyTaxon instance.
        """
        matches = self.get_taxa_with_taxon_author_tolerance(taxon_source, taxon_latname, taxon_author)

        if len(matches) == 0:
            raise ValueError('No matching taxon found for {0} {1} in {2}'.format(taxon_latname, taxon_author, taxon_source))
        
        if len(matches) > 1:
            raise ValueError('Multiple matching taxa found for {0} {1} in {2}'.format(taxon_latname, taxon_author, taxon_source))

        return LazyTaxon(instance=matches[0])
    
    
    def get_lazy_taxon(self, taxon_latname, taxon_source, taxon_author=None):

        models = TaxonomyModelRouter(taxon_source)

        field_kwargs = {
            'taxon_latname' : taxon_latname,
        }

        if taxon_author:
            field_kwargs['taxon_author'] = taxon_author

        try:
            taxon = models.TaxonTreeModel.objects.get(**field_kwargs)
            lazy_taxon = LazyTaxon(instance=taxon)
            return lazy_taxon
        except models.TaxonTreeModel.DoesNotExist:
            # fallback to tolerance method
            return self.get_lazy_taxon_with_tolerance(taxon_latname, taxon_source, taxon_author)
    
    
    def validate_square_image(self, image_filepath):
        
        filename = os.path.basename(image_filepath)
        
        im = Image.open(image_filepath)
        width, height = im.size

        if width != height:
            message = _('Image is not square: %(filename)s' % {
                'filename' : filename,
            })

            self.errors.append(message)
            
        if height > IMAGE_MAX_HEIGHT:
            message = _('Image height is too large: %(filename)s. Maximum allowed height is %(max_height)s' % {
                'filename' : filename,
                'max_height' : IMAGE_MAX_HEIGHT,
            })

            self.errors.append(message)
            
        
        if width > IMAGE_MAX_WIDTH:
            message = _('Image width is too large: %(filename)s. Maximum allowed width is %(max_width)s' % {
                'filename' : filename,
                'max_width' : IMAGE_MAX_WIDTH,
            })
            self.errors.append(message)
import os, shutil

from PIL import Image

# widths of the ouput image
# the height depends on the crop area set by the user
IMAGE_SIZES = {
    'regular' : {
        '1x' : 250,
        '2x' : 500,
        '4x' : 1000,
    },
    'large' : {
        '4x' : 1000,
        '8x' : 2000,
    },
    'all' : {
        '1x' : 250,
        '2x' : 500,
        '4x' : 1000,
        '8x' : 2000,
    }
}

class ContentImageBuilder:

    def __init__(self):
        self.image_cache = {}

    def build_content_image(self, content_image, absolute_path, relative_path, image_sizes='regular'):

        image_urls = {}
        
        for size_name, size in IMAGE_SIZES[image_sizes].items():

            cache_key = '{0}-{1}'.format(content_image.id, size)

            if cache_key in self.image_cache:
                image_urls[size_name] = self.image_cache[cache_key]

            else:

                if not os.path.isdir(absolute_path):
                    os.makedirs(absolute_path)

                source_image_path = content_image.image_store.source_image.path

                # no image processing for svgs
                if source_image_path.endswith('.svg'):

                    filename = '{0}-{1}.svg'.format(content_image.id, content_image.image_type)
                    
                    relative_image_filepath = os.path.join(relative_path, filename)
                    absolute_image_filepath = os.path.join(absolute_path, filename)

                    shutil.copyfile(source_image_path, absolute_image_filepath)

                else:
                    
                    original_image = Image.open(source_image_path)
                    processed_image = content_image.get_in_memory_processed_image(original_image, size)

                    # all processed images are webp
                    #original_format = original_image.format
                    #output_format = original_format
                    #allowed_formats = ['png', 'jpg', 'jpeg']

                    file_extension = 'webp'
                    output_format = 'WEBP'

                    output_filename = '{0}-{1}-{2}.{3}'.format(content_image.image_type, content_image.id, size,
                            file_extension)

                    relative_image_filepath = os.path.join(relative_path, output_filename)
                    absolute_image_filepath = os.path.join(absolute_path, output_filename)

                    if not os.path.isfile(absolute_image_filepath):
                        processed_image.save(absolute_image_filepath, output_format)
                
                image_urls[size_name] = relative_image_filepath        
        
        return image_urls
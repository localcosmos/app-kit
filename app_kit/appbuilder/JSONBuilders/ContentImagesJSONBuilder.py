from app_kit.models import ContentImage

# uses ContentimageBuilder which also manages the Cache
class ContentImagesJSONBuilder:
    
    def __init__(self, app_release_builder):
        
        self.app_release_builder = app_release_builder
    
    
    def _get_content_image(self, content_image_mixedin, image_type='image'):

        if type(content_image_mixedin) == ContentImage:
            content_image = content_image_mixedin
        else:
            content_image = content_image_mixedin.image(image_type=image_type)

        return content_image

    # images_sizes = [] means that the image_sizes will be set by app_release_builder.build_content_image
    def _get_image_urls(self, content_image_mixedin, image_type='image', image_sizes=[]):

        content_image = self._get_content_image(content_image_mixedin, image_type=image_type)

        if content_image:
            image_urls = self.app_release_builder.build_content_image(content_image, image_sizes=image_sizes)

        else:
            image_urls = self.app_release_builder.no_image_url
            
        return image_urls 


    def _get_image_licence(self, content_image_mixedin, image_type='image'):
        if type(content_image_mixedin) == ContentImage:
            content_image = content_image_mixedin
        else:
            content_image = content_image_mixedin.image(image_type=image_type)

        licence = self.app_release_builder.content_image_builder.build_licence(content_image)
        return licence
    
    '''
        The licences are read from  LicenceRegistry
    '''
    def get_image_json(self, content_image_mixedin):

        image_urls = self._get_image_urls(content_image_mixedin)
        #licence = {}

        #if image_urls:
        #    licence = self._get_image_licence(content_image_mixedin)

        image_entry = {
            'text': content_image_mixedin.text, # = caption
            'altText': content_image_mixedin.alt_text,
            'title': content_image_mixedin.title,
            'imageUrl' : image_urls,
            #'licence' : licence,
        }

        return image_entry

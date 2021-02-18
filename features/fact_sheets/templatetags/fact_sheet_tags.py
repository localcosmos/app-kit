from django.conf import settings
from django import template
register = template.Library()

from django.template import loader, Context
from django.utils.safestring import mark_safe


from django.db.models import Q


from app_kit.features.fact_sheets.models import FactSheetImages

'''
    cms_get
    - fetch content from db / declare a user-defineable content
    - template_content_specific (template_content in context)
    - base.html (template_content not in context)    
'''
def cms_get(context, microcontent_category, microcontent_type, *args, **kwargs):

    build = context.get('build', False)

    fact_sheet = context['fact_sheet']
    language_code = context.get('language_code', fact_sheet.fact_sheets.primary_language)
    

    if microcontent_category == 'microcontent':

        if fact_sheet.contents:
            fallback = ' '.join(microcontent_type.split('_'))
            content = fact_sheet.contents.get(microcontent_type, fallback)
            if type(content) == str:
                return mark_safe(content)
            return content

    elif microcontent_category == 'image':

        content = FactSheetImages.objects.filter(fact_sheet=fact_sheet,
                                                 microcontent_type=microcontent_type).first()

        if content:

            content.build = build
            content.language_code = language_code

        return content

    return ''


'''
    cms_get_multiple
    - fetch multiple contents of the same microcontent_category+microcontent_type from db
'''
@register.simple_tag(takes_context=True)
def cms_get_multiple(context, microcontent_category, microcontent_type, *args, **kwargs):

    build = context.get('build', False)

    fact_sheet = context['fact_sheet']
    language_code = context.get('language_code', fact_sheet.fact_sheets.primary_language)
    
    if microcontent_category == 'microcontent':

        if fact_sheet.contents:
            contents =  fact_sheet.contents.get(microcontent_type, [])

    elif microcontent_category in ['image', 'images']:

        images = []
        
        images_qry = FactSheetImages.objects.filter(fact_sheet=fact_sheet,
                                                 microcontent_type=microcontent_type)

        for image in images_qry:
            image.build = build
            image.language_code = language_code

            images.append(image)
            
        return images

    return []


'''
    shortcuts for getting MicroContent
'''
@register.simple_tag(takes_context=True)
def cms_get_microcontent(context, microcontent_type, *args, **kwargs):
    html = cms_get(context, 'microcontent', microcontent_type, *args, **kwargs)
    return html


@register.simple_tag(takes_context=True)
def cms_get_microcontents(context, microcontent_type, *args, **kwargs):
    html = cms_get_multiple(context, 'microcontents', microcontent_type, *args, **kwargs)
    return html


@register.simple_tag(takes_context=True)
def cms_get_image(context, microcontent_type, *args, **kwargs):
    image = cms_get(context, 'image', microcontent_type, *args, **kwargs)
    return image

'''
    multiple images
'''
@register.simple_tag(takes_context=True)
def cms_get_images(context, microcontent_type, *args, **kwargs):
    image = cms_get_multiple(context, 'image', microcontent_type, *args, **kwargs)
    return image


@register.simple_tag
def image_url(image):
    try:
        return image.url
    except:
        return ''

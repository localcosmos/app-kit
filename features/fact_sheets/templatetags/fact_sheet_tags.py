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

    fact_sheet = context['fact_sheet']

    if microcontent_category == 'microcontent':

        if fact_sheet.contents:
            
            content = fact_sheet.contents.get(microcontent_type, '')
            if type(content) == str:
                return mark_safe(content)
            return content

    elif microcontent_category == 'image':

        content = FactSheetImages.objects.filter(fact_sheet=fact_sheet,
                                                 microcontent_type=microcontent_type).first()

        return content

    return ''


'''
    cms_get_multiple
    - fetch multiple contents of the same microcontent_category+microcontent_type from db
'''
@register.simple_tag(takes_context=True)
def cms_get_multiple(context, microcontent_category, microcontent_type, *args, **kwargs):

    fact_sheet = context['fact_sheet']
    
    if microcontent_category == 'microcontent':

        if fact_sheet.contents:
            return fact_sheet.contents.get(microcontent_type, [])

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

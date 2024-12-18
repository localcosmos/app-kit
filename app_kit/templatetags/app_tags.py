from django.conf import settings
from django import template
register = template.Library()

from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.templatetags.static import static
from django.contrib.staticfiles import finders

from app_kit.models import MetaApp


from django.contrib.contenttypes.models import ContentType
from taxonomy.lazy import LazyTaxon


@register.filter
def verbose_name(obj):
    return obj._meta.verbose_name


@register.filter
def ranged(number):
    return range(1,int(number)+1)


from app_kit.models import ContentImage
@register.simple_tag
def content_image(instance, image_type=None):

    content_type = ContentType.objects.get_for_model(instance)

    image = None

    if image_type:
        image = ContentImage.objects.filter(content_type=content_type, object_id=instance.id, image_type=image_type).first()
    else:
        image = ContentImage.objects.filter(content_type=content_type, object_id=instance.id).first()

    if image:
        return image.image_url()

    return image


@register.filter
def classpath(instance):
    ctype = ContentType.objects.get_for_model(instance)
    return '{0}.models.{1}'.format(ctype.app_label, instance.__class__.__name__)


@register.inclusion_tag('app_kit/content_images.html')
def render_content_images(meta_app, content_object):

    images = []

    if content_object:
        pass

    context = {
        'meta_app': meta_app,
        'content_object' : content_object,
        'images' : images,
    }
    
    return context

@register.filter
def clean_taxa(lazy_taxon_list):
    cleaned = []
    for taxon in lazy_taxon_list:

        exists = False
        
        for added_taxon in cleaned:
            
            # taxon is parent of added -> replace
            if added_taxon.taxon_include_descendants == True and added_taxon.taxon_nuid.startswith(taxon.taxon_nuid):
                cleaned[cleaned.index(added_taxon)] = taxon
                exists = True
                break
            # taxon is child of added -> skip
            elif taxon.taxon_include_descendants == True and taxon.taxon_nuid.startswith(added_taxon.taxon_nuid):
                exists = True
                break

        if not exists:
            cleaned.append(taxon)
            
    return cleaned


@register.filter
def taxon_origin(lazy_taxon):

    origin = lazy_taxon.__class__.__name__
    
    if hasattr(lazy_taxon, 'instance') and lazy_taxon.instance:
        origin = lazy_taxon.instance.__class__.__name__

    if origin == 'MetaNode' or origin == 'NatureGuidesTaxonTree':
        return lazy_taxon.nature_guide

    return origin
    


@register.filter
def localize(dic, language):
    if language in dic:
        return dic[language]

    elif len(dic.keys()) > 0:
        return dic[dic.keys()[0]]
    
    return 'unnamed'



@register.simple_tag(takes_context=True)
def get_generic_content_options(context, generic_content):
    meta_app = context['meta_app']
    link = meta_app.get_generic_content_link(generic_content)
    return link.options


@register.simple_tag(takes_context=True)
def get_generic_content_option(context, generic_content, option):
    meta_app = context['meta_app']
    link = meta_app.get_generic_content_link(generic_content)

    if link.options and option in link.options:
        return link.options[option]

    return None


@register.filter
def generic_content_link_deletable(generic_content_link):
    
    addable_features = generic_content_link.meta_app.addable_features()

    class_names = [c.__name__ for c in addable_features]

    if generic_content_link.generic_content.__class__.__name__ in class_names:
        return True
    return False


@register.filter
def generic_content_may_have_image(generic_content):
    
    if generic_content.__class__.__name__ == 'NatureGuide':
        return True

    return False


'''
    this is currently ununsed, but might be useful in the future
'''
@register.simple_tag
def taxonfilter_image_url(latname):

    filepath = 'app_kit/buttons/taxonfilters/%s.svg' % latname

    abs_path = finders.find(filepath)
    if abs_path:
        return static(filepath)

    return static('app_kit/buttons/taxonfilters/Customfilter.svg')
    

@register.filter
def vernacular(taxon, language):
    return taxon.vernacular(language)


@register.simple_tag
def get_vernacular(taxon, language, cache=None):
    
    if type(taxon) == dict:
        taxon = LazyTaxon(**taxon)

    if cache:
        try:
            return cache[self.taxon_source][self.name_uuid][language]
        except:
            return None
    
    return taxon.vernacular(language, cache)

@register.simple_tag
def supply_vernacular_names(taxon_cache, language, vernacular_cache):
    for taxon_link in taxon_cache:
        try:
            taxon_link['temporary_vernacular'] = vernacular_cache.cache[taxon_link['taxon_source']][taxon_link['name_uuid']][language]
        except:
            taxon_link['temporary_vernacular'] = None
    return taxon_cache

   

import datetime
@register.filter
def timestamp_to_datetime(timestamp):
    return datetime.datetime.fromtimestamp(int(timestamp)) 


@register.simple_tag
def get_meta_app(app):
    if app:
        meta_app = MetaApp.objects.get(app=app)
    else:
        meta_app = None
    return meta_app



GENERIC_CONTENT_HELP_TEXTS = {
    'BackboneTaxonomy' : _('Manage the taxa of this app. The taxa defined in the backbone taxonomy are available in observation forms and taxon profiles. Taxa of nature guides are automatically added to the backbone.'),
    'Glossary' : _('Where a glossary entry appears, the user can click on it to read the explanation.'),
    'NatureGuide' : _('A Nature Guide is an identification key or a simple species list.'),
    'Map' : _('The map feature plots your observations on a map.'),
    'TaxonProfiles' : _('Describe the species of your app using taxon profiles.'),
    'GenericForm': _('An observation form is used to collect data.'),
    'Frontend' : _('Defines the visual appearance of your app'),
    'App' : '',
}

@register.simple_tag
def get_generic_content_help_text(generic_content):

    if generic_content.__class__.__name__ == 'ModelBase':
        key = generic_content.__name__
    else:
        key = generic_content.__class__.__name__

    help_text = GENERIC_CONTENT_HELP_TEXTS.get(key, _('No help text available.'))
    
    return help_text


# LEGAL
@register.simple_tag(takes_context=True)
def root_url(context, url_name, *args):

    url = reverse(url_name, args=args, urlconf=settings.PUBLIC_SCHEMA_URLCONF)

    request = context['request']

    if request.tenant.schema_name != 'public':
        host = '.'.join(request.META['HTTP_HOST'].split('.')[1:])
    else:
        host = request.META['HTTP_HOST']
        
    root_url = '{0}://{1}{2}'.format(request.scheme, host, url)
    
    return root_url
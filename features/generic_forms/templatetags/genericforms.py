from django.conf import settings
from django import template
register = template.Library()

from django.utils import translation
from django.utils.translation import gettext_lazy as _

from app_kit.features.generic_forms.models import (DJANGO_FIELD_CLASSES, DJANGO_FIELD_WIDGETS)

from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from django import forms

from app_kit.features.generic_forms.forms import DynamicField, DynamicForm

@register.inclusion_tag('generic_forms/generic_field.html')
def render_generic_field(generic_field_link, meta_app):

    language = generic_field_link.generic_form.primary_language
    
    dynamic_field = DynamicField(generic_field_link, language, meta_app)
        
    form = DynamicForm([dynamic_field])
    
    return {'generic_field' : generic_field_link.generic_field, 'django_field' : form.visible_fields()[0] }


@register.filter
def fieldform_title(fieldform):

    if fieldform.is_bound:
        widget = fieldform['widget'].data
        generic_field_class = fieldform['generic_field_class'].data
    else:
        widget = fieldform.initial['widget']
        generic_field_class = fieldform.initial['generic_field_class']
        
    c = dict(DJANGO_FIELD_CLASSES)
    class_verbose = c[generic_field_class]

    w = dict(DJANGO_FIELD_WIDGETS)
    widget_verbose = w[widget]

    if generic_field_class == 'ChoiceField':
        title = "%s (%s)" %(class_verbose, widget_verbose)
    else:
        title = class_verbose

    return title

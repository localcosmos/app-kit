from django.conf import settings
from django import template
register = template.Library()

from app_kit.features.buttonmatrix.models import ButtonMatrixButton

from django.utils.translation import gettext_lazy as _

@register.inclusion_tag('buttonmatrix/buttonmatrix_button.html', takes_context=True)
def render_buttonmatrix_button(context, meta_app, button_matrix, row, column):

    button = ButtonMatrixButton.objects.language(meta_app.primary_language).filter(button_matrix=button_matrix, row=row,
                                                                                column=column).first()

    ctx = {
        "meta_app" : context["meta_app"],
        "button" : button,
        "row" : row,
        "column" : column,
        "button_matrix" : button_matrix,
    }
    
    return ctx

from app_kit.features.generic_forms.forms import DynamicField
from django import forms
@register.inclusion_tag('generic_forms/generic_field.html')
def render_exposed_field(generic_field_link, language):

    if not language:
        raise ValueError('no language given')
    
    dynamic_field = DynamicField(generic_field_link, language)
        
    form = forms.Form()
    form.fields['exposed_field'] = dynamic_field.django_field
    
    return {'generic_field' : generic_field_link.generic_field, 'django_field' : form.visible_fields()[0] }

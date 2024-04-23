import re
from django.conf import settings

def import_module(module):
    module = str(module)
    d = module.rfind(".")
    module_name = module[d+1:len(module)]
    m = __import__(module[0:d], globals(), locals(), [module_name])
    return getattr(m, module_name)

def import_class(cl):
    d = cl.rfind(".")
    classname = cl[d+1:len(cl)]
    m = __import__(cl[0:d], globals(), locals(), [classname])
    return getattr(m, classname)


from django.urls import reverse
def get_appkit_taxon_search_url():
    return reverse('search_taxon')


from django.forms.models import model_to_dict
from django.db.models import ForeignKey, ManyToManyField
def copy_model_instance(instance, copy_fields, overwrite_values={}):

    Model = type(instance)

    instance_dict = model_to_dict(instance, fields=copy_fields)

    regular_fields = {}
    m2m_fields = {}

    for field_name, value in instance_dict.items():

        model_field = instance._meta.get_field(field_name)

        if isinstance(model_field, ForeignKey):
            regular_fields[field_name] = getattr(instance, field_name)

        elif isinstance(model_field, ManyToManyField):
            # m2m fields have to be populated after save
            old_field_value = getattr(instance, field_name)
            m2m_fields[field_name] = old_field_value.all()

        else:
            regular_fields[field_name] = value


    regular_fields.update(overwrite_values)
    
    instance_copy = Model(**regular_fields)
    instance_copy.save()

    for m2m_field, m2m_query in m2m_fields.items():
        field = getattr(instance_copy, m2m_field)
        field.set(m2m_query)

    return instance_copy


def unCamelCase(string):
    return re.sub(r"(\w)([A-Z])", r"\1 \2", string).title()

def camelCase_to_underscore_case(string):

    spaced = re.sub(r"(\w)([A-Z])", r"\1 \2", string).lower()
    spaced_parts = spaced.split(' ')

    underscored = '_'.join(spaced_parts)

    return underscored

def underscore_to_camelCase(string):
    under_pat = re.compile(r'_([a-z])')
    return under_pat.sub(lambda x: x.group(1).upper(), string)
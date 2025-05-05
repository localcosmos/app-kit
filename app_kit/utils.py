import re
from django.contrib.contenttypes.models import ContentType
from app_kit.features.generic_forms.models import GenericFieldToGenericForm

from localcosmos_server.utils import get_content_instance_app

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


'''
    given a model instance, check which app it belongs to
    - ModelWithRequiredTaxon
        - AppContentTaxonomicRestriction
            - GenericForm
            - GenericField
        - BackboneTaxa
        - FilterTaxon
        - TaxonProfile
        - TaxonProfilesNavigationEntryTaxa
    - ModelWithTaxon
        - MetaNode
        - ImageStore
    - ContentImageMixin
        - MetaApp
        - Frontend
        - GlossaryEntry
        - NatureGuide
        - MetaNode
        - NatureGuidesTaxonTree
        - MatrixFilterSpace
        - TaxonProfile
        - TaxonProfilesNavigationEntry
'''

def get_generic_content_meta_app(instance):
    from app_kit.models import MetaAppGenericContent
    meta_app = None
    content_type = ContentType.objects.get_for_model(instance)
    links = MetaAppGenericContent.objects.filter(content_type=content_type, object_id=instance.id)
    if links.count() > 1:
        raise Exception(f'More than one MetaAppGenericContent found for {instance.__class__.__name__})')
    
    elif links:
        link = links.first()
        meta_app = link.meta_app
        
    return meta_app 

def get_content_instance_meta_app(instance):
    from app_kit.models import MetaApp, ContentImage
    if instance.__class__.__name__ == 'AppContentTaxonomicRestriction':
        if instance.content.__class__.__name__ == 'GenericForm':
            return get_generic_content_meta_app(instance.content)
        
        elif instance.content.__class__.__name__ == 'GenericField':
            field_link = GenericFieldToGenericForm.objects.filter(generic_field=instance.content).first()
            return get_generic_content_meta_app(field_link.generic_form)
        
    elif instance.__class__.__name__ == 'BackboneTaxa':
        return get_generic_content_meta_app(instance.backbonetaxonomy)
    elif instance.__class__.__name__ == 'FilterTaxon':
        return get_generic_content_meta_app(instance.taxonomic_filter.map)
    elif instance.__class__.__name__ == 'TaxonProfile':
        return get_generic_content_meta_app(instance.taxon_profiles)
    elif instance.__class__.__name__ == 'TaxonProfilesNavigationEntryTaxa':
        return get_generic_content_meta_app(instance.navigation_entry.navigation.taxon_profiles)
    elif instance.__class__.__name__ == 'MetaNode':
        return get_generic_content_meta_app(instance.nature_guide)        
    elif instance.__class__.__name__ in ['BackboneTaxonomy', 'TaxonProfiles', 'NatureGuide', 'Map', 'GenericForm', 'Frontend', 'Glossary']:
        return get_generic_content_meta_app(instance)
    elif instance.__class__.__name__ == 'MetaApp':
        return instance
    elif instance.__class__.__name__ == 'GlossaryEntry':
        return get_generic_content_meta_app(instance.glossary)
    elif instance.__class__.__name__ == 'MatrixFilterSpace':
        return get_generic_content_meta_app(instance.matrix_filter.meta_node.nature_guide)
    elif instance.__class__.__name__ == 'TaxonProfilesNavigationEntry':
        return get_generic_content_meta_app(instance.navigation.taxon_profiles)
    elif instance.__class__.__name__ == 'GenericField':
        field_link = GenericFieldToGenericForm.objects.filter(generic_field=instance).first()
        return get_generic_content_meta_app(field_link.generic_form)
    elif instance.__class__.__name__ == 'ImageStore':
        content_image = ContentImage.objects.filter(image_store=instance).first()
        if content_image:
            meta_app = get_generic_content_meta_app(content_image.content)
            return meta_app
        else:
            return None
    elif instance.__class__.__name__ in ['Dataset', 'DatasetValidationRoutine', 'ServerImageStore']:
        app = get_content_instance_app(instance)
        if app:
            meta_app = MetaApp.objects.get(app__uuid=app.uuid)
            return meta_app
        else:
            return None
    else:
        # raise error
        raise NotImplementedError(f'get_generic_content_meta_app not implemented for {instance.__class__.__name__}')
from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.object_classes.models import ObjectClass, ObjectClassTaxon


'''
    Builds JSON for one ObjectClasses feature.

    The JSON is optimised for fast client-side lookup in observation forms:

    universalClasses  – scientific_names of classes with no taxa assigned;
                        shown as initial choices before any taxon is selected.

    classes           – dict keyed by scientific_name with display data;
                        used for O(1) detail lookup after the scientific_name
                        is resolved from taxonMap.

    taxonMap          – pre-inverted index: {taxon_source: {taxon_nuid: [scientific_names]}}.
                        Client walks the observed taxon's ancestor nuids and unions the hits.
                        Lookup is O(nuid_depth), independent of the number of classes.
'''
class ObjectClassesJSONBuilder(JSONBuilder):

    def build(self):

        object_classes_json = self._build_common_json()

        object_classes = self.generic_content

        for category in ('object_class', 'morphotype'):
            section_key = 'objectClasses' if category == 'object_class' else 'morphotypes'

            all_classes = ObjectClass.objects.filter(
                object_classes=object_classes, category=category
            ).prefetch_related('taxon_mappings')

            classes_dict = {}
            universal_classes = []
            taxon_map = {}

            for obj_class in all_classes:
                classes_dict[obj_class.scientific_name] = {
                    'name': obj_class.name,
                    'description': obj_class.description,
                }

                taxon_mappings = list(obj_class.taxon_mappings.all())

                if not taxon_mappings:
                    universal_classes.append(obj_class.scientific_name)
                else:
                    for taxon_mapping in taxon_mappings:
                        source = taxon_mapping.taxon_source
                        nuid = taxon_mapping.taxon_nuid

                        if source not in taxon_map:
                            taxon_map[source] = {}

                        if nuid not in taxon_map[source]:
                            taxon_map[source][nuid] = []

                        taxon_map[source][nuid].append(obj_class.scientific_name)

            object_classes_json[section_key] = {
                'universalClasses': universal_classes,
                'classes': classes_dict,
                'taxonMap': taxon_map,
            }

        return object_classes_json


from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.maps.models import Map, MapGeometries, MapTaxonomicFilter
from app_kit.features.generic_forms.models import GenericForm

from django.contrib.gis.gdal import SpatialReference, CoordTransform

import json

'''
    Builds JSON for one TaxonProfiles
'''
class MapJSONBuilder(JSONBuilder):

    def serialize_project_area(self, project_area):
        geojson = {
            "type":"FeatureCollection",
            "features": []
        }

        for geometry in project_area.geometry:

            map_sr = SpatialReference(4326)
            db_sr = SpatialReference(3857)
            trans = CoordTransform(db_sr, map_sr)

            geometry.transform(trans)

            feature = {
                "type":"Feature",
                "properties":{},
                "geometry": json.loads(geometry.geojson),
            }

            geojson['features'].append(feature)

        return geojson

    def build(self):

        map = self.app_generic_content.generic_content
        map_json = self._build_common_json()

        map_json.update({
            'mapType' : map.map_type,
            'geometries' : {},
            'taxonomicFilters' : [],
            'observationFormFilters' : [],
        })

        # optionally add project area
        project_area = MapGeometries.objects.filter(map=map, geometry_type='project_area').first()

        if project_area:
            geojson = self.serialize_project_area(project_area)

            map_json['geometries']['projectArea'] = geojson
        
        taxonomic_filters = MapTaxonomicFilter.objects.filter(map=map)

        for taxonomic_filter in taxonomic_filters:
            filter_entry = {
                'name': taxonomic_filter.name,
                'taxa': [],
                'position': taxonomic_filter.position,
            }

            for taxon in taxonomic_filter.taxa:
                taxon_entry = self.app_release_builder.taxa_builder.serialize_taxon(taxon)
                filter_entry['taxa'].append(taxon_entry)

            map_json['taxonomicFilters'].append(filter_entry)

        include_generic_forms = map.get_option(self.meta_app, 'include_observation_forms_as_filters')

        if include_generic_forms == True:
            generic_form_links = self.meta_app.get_generic_content_links(GenericForm)
            for generic_form_link in generic_form_links:

                generic_form = generic_form_link.generic_content

                generic_form_filter = {
                    'observationFormUuid' : str(generic_form.uuid),
                    'name' : generic_form.name,
                }

                map_json['observationFormFilters'].append(generic_form_filter)

        return map_json
    

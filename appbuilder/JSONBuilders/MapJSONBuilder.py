from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.maps.models import Map, MapGeometries

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

        lc_map = self.app_generic_content.generic_content
        map_json = self._build_common_json()

        map_json.update({
            'map_type' : lc_map.map_type,
            'geometries' : {},
        })

        # optionally add project area
        project_area = MapGeometries.objects.filter(map=lc_map, geometry_type='project_area').first()

        if project_area:
            geojson = self.serialize_project_area(project_area)

            map_json['geometries']['project_area'] = geojson

        return map_json
    

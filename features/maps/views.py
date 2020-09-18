from django.views.generic import FormView, TemplateView
from django.utils.decorators import method_decorator
from django.core.serializers import serialize
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.contrib.gis.gdal import SpatialReference, CoordTransform

from localcosmos_server.decorators import ajax_required

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin

from .forms import MapsOptionsForm, ProjectAreaForm

from .models import Map, MapGeometries

import json
        
class ManageMaps(ManageGenericContent):

    template_name = 'maps/manage_maps.html'
    options_form_class = MapsOptionsForm


PROJECT_AREA_TYPE = 'project_area'
class ManageProjectArea(MetaAppMixin, FormView):

    template_name = 'maps/ajax/manage_project_area.html'
    form_class = ProjectAreaForm

    def dispatch(self, request, *args, **kwargs):
        self.map = Map.objects.get(pk=kwargs['object_id'])
        self.project_area = MapGeometries.objects.filter(map=self.map, geometry_type=PROJECT_AREA_TYPE).first()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['map'] = self.map
        
        context['project_area'] = None
        if self.project_area:
            context['project_area'] = self.serialize_project_area()
        
        context['success'] = False
        return context

    def serialize_project_area(self):

        geojson = {
            "type":"FeatureCollection",
            "features": [
                #{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[5.097656,48.004625],[5.097656,50.541363],[10.83252,50.541363],[10.83252,48.004625],[5.097656,48.004625]]]}},
            ]
        }

        for geometry in self.project_area.geometry:

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

    def get_initial(self):
        initial = super().get_initial()

        if self.project_area:
            geojson = self.serialize_project_area()
            initial['area'] = json.dumps(geojson)

        return initial

    def remove_project_area(self):
        if self.project_area:
            self.project_area.delete()
            
        self.project_area = None

    def form_valid(self, form):

        geojson_str = form.cleaned_data.get('area', None)

        if not geojson_str or len(geojson_str) == 0:
            self.remove_project_area()

        else:
            geojson = json.loads(geojson_str)

            if len(geojson['features']) == 0:
                self.remove_project_area()

            else:
                # new area -> save
                if not self.project_area:
                    self.project_area = MapGeometries(
                        map = self.map,
                        geometry_type = PROJECT_AREA_TYPE,
                    )

                '''
                {"type":"FeatureCollection","features":[
                    {"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[5.097656,48.004625],[5.097656,50.541363],[10.83252,50.541363],[10.83252,48.004625],[5.097656,48.004625]]]}},
                    {"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[1.40625,46.649436],[1.40625,48.034019],[3.779297,48.034019],[3.779297,46.649436],[1.40625,46.649436]]]}}]}
                '''
                polygons = []

                for feature in geojson['features']:
                    polygon = GEOSGeometry(json.dumps(feature['geometry']), srid=4326)
                    polygons.append(polygon)
                    
                multipoly = MultiPolygon(tuple(polygons), srid=4326)

                self.project_area.geometry = multipoly
                self.project_area.save()
                self.project_area.refresh_from_db()

        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True

        return self.render_to_response(context)
        
        

    

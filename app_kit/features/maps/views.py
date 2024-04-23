from django.views.generic import FormView, TemplateView
from django.utils.decorators import method_decorator
from django.core.serializers import serialize
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from localcosmos_server.decorators import ajax_required

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin, MetaAppFormLanguageMixin

from app_kit.features.generic_forms.models import GenericForm

from localcosmos_server.generic_views import AjaxDeleteView

from .forms import MapsOptionsForm, ProjectAreaForm, TaxonomicFilterForm

from .models import Map, MapGeometries, MapTaxonomicFilter, FilterTaxon

import json
        
class ManageMaps(ManageGenericContent):

    template_name = 'maps/manage_maps.html'
    options_form_class = MapsOptionsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_area'] = MapGeometries.objects.filter(map=self.generic_content,
            geometry_type=PROJECT_AREA_TYPE).first()
        context['taxonomic_filters'] = MapTaxonomicFilter.objects.filter(map=self.generic_content)
        context['map_taxonomic_filter_content_type'] = ContentType.objects.get_for_model(MapTaxonomicFilter)
        context['observation_form_links'] = self.meta_app.get_generic_content_links(GenericForm)
        return context


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

            #map_sr = SpatialReference(4326)
            #db_sr = SpatialReference(3857)
            #trans = CoordTransform(db_sr, map_sr)

            #geometry.transform(trans)

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


class ManageTaxonomicFilter(MetaAppFormLanguageMixin, FormView):

    form_class = TaxonomicFilterForm
    template_name = 'maps/ajax/manage_taxonomic_filter.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxonomic_filter(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_taxonomic_filter(self, **kwargs):
        self.taxonomic_filter = None
        if 'taxonomic_filter_id' in kwargs:
            self.taxonomic_filter = MapTaxonomicFilter.objects.get(pk=kwargs['taxonomic_filter_id'])

        self.map = Map.objects.get(pk=kwargs['map_id'])
        self.content_type = ContentType.objects.get_for_model(Map)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxonomic_filter'] = self.taxonomic_filter
        context['map'] = self.map
        context['content_type'] = self.content_type
        context['success'] = False

        add_single_form_form_kwargs =  {
            'taxon_search_url' : reverse('search_taxon'),
            'descendants_choice' : False,
        }
        context['add_taxon_form'] = AddSingleTaxonForm(**add_single_form_form_kwargs)
        return context

    def get_initial(self):
        initial = super().get_initial()
        if self.taxonomic_filter:
            initial['name'] = self.taxonomic_filter.name
        return initial


    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['taxonomic_filter'] = self.taxonomic_filter
        return form_kwargs


    def form_valid(self, form):
        
        filter_name = form.cleaned_data['name']

        taxon_to_add = form.cleaned_data['taxon']

        if not self.taxonomic_filter:
            self.taxonomic_filter = MapTaxonomicFilter(
                map = self.map,
            )

        self.taxonomic_filter.name = filter_name

        self.taxonomic_filter.save()

        # add taxon to taxon_list if it does not exist yet
        if taxon_to_add:
            filter_taxon = FilterTaxon(taxonomic_filter=self.taxonomic_filter)
            filter_taxon.set_taxon(taxon_to_add)
            filter_taxon.save()

        context = self.get_context_data(**self.kwargs)

        # provide an empty taxon field
        form_kwargs = self.get_form_kwargs()
        if 'data' in form_kwargs:
            del form_kwargs['data']
        if 'files' in form_kwargs:
            del form_kwargs['files']
        context['form'] = self.form_class(**form_kwargs)
        context['success'] = True
        return self.render_to_response(context)


class GetTaxonomicFilters(MetaAppMixin, TemplateView):

    template_name = 'maps/ajax/taxonomic_filters.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        map = Map.objects.get(pk=kwargs['map_id'])
        context['taxonomic_filters'] = MapTaxonomicFilter.objects.filter(map=map)
        context['map_taxonomic_filter_content_type'] = ContentType.objects.get_for_model(MapTaxonomicFilter)
        context['generic_content'] = map
        return context



class DeleteTaxonomicFilter(AjaxDeleteView):
    model = MapTaxonomicFilter


class DeleteFilterTaxon(MetaAppMixin, AjaxDeleteView):
    model = FilterTaxon

    template_name = 'maps/ajax/delete_filter_taxon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['map'] = Map.objects.get(pk=self.kwargs['map_id'])
        context['taxonomic_filter'] = MapTaxonomicFilter.objects.get(pk=self.kwargs['taxonomic_filter_id'])
        return context
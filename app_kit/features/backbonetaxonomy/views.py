from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView, FormView, UpdateView
from django.utils.decorators import method_decorator
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from app_kit.views import ManageGenericContent
from app_kit.models import MetaApp, MetaAppGenericContent
from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa
from app_kit.features.taxon_profiles.models import TaxonProfiles, TaxonProfile
from app_kit.features.nature_guides.models import NatureGuide, NatureGuidesTaxonTree
from app_kit.utils import get_appkit_taxon_search_url
from app_kit.view_mixins import MetaAppMixin

from localcosmos_server.decorators import ajax_required
from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from .forms import (AddMultipleTaxaForm, ManageFulltreeForm, SearchTaxonomicBackboneForm, SwapTaxonForm)

from .utils import TaxonManager, TaxonReferencesUpdater

from taxonomy.models import TaxonomyModelRouter

from taxonomy.lazy import LazyTaxon

import json

class ManageBackboneTaxonomy(ManageGenericContent):

    template_name = 'backbonetaxonomy/manage_backbonetaxonomy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ajax pagination template
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.template_name = 'backbonetaxonomy/taxonlist.html'

        # if the querystring_key is present, only render partially for ajax pagination
        if 'contenttypeid' in self.request.GET:
            content_type = ContentType.objects.get(pk=self.request.GET['contenttypeid'])
            generic_content = content_type.get_object_for_this_type(pk=self.request.GET['objectid'])
                
            context['taxa'] = self.meta_app.all_taxa()
            context['alltaxa'] = False
            
        else:

            # backbonetaxonomy
            feature = MetaAppGenericContent.objects.get(
                meta_app = self.meta_app,
                content_type = ContentType.objects.get_for_model(BackboneTaxonomy),
            )

            context['alltaxa'] = True
            context['taxa'] = self.meta_app.all_taxa()

            form_kwargs = {
                'taxon_search_url': get_appkit_taxon_search_url(),
                'descendants_choice' : True,
            }
            
            context['form'] = AddSingleTaxonForm(**form_kwargs)
            context['taxaform'] = AddMultipleTaxaForm()
            context['fulltreeform'] = ManageFulltreeForm(instance=self.generic_content)

            backbone_search_form_kwargs = {
                'taxon_search_url': reverse('search_backbonetaxonomy', kwargs={'meta_app_id':self.meta_app.id}),
                'fixed_taxon_source' : '__all__',
                'prefix' : 'backbone',
            }
            context['searchbackboneform'] = SearchTaxonomicBackboneForm(**backbone_search_form_kwargs)
        
        return context


class BackboneFulltreeUpdate(UpdateView):

    form_class = ManageFulltreeForm
    model = BackboneTaxonomy
    template_name = 'backbonetaxonomy/manage_fulltree_form.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.backbone = BackboneTaxonomy.objects.get(pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['backbone'] = self.backbone
        context['content_type'] = ContentType.objects.get_for_model(BackboneTaxonomy)
        return context

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)

        backbone = form.save(commit=False)

        include_full_tree = form.cleaned_data['include_full_tree']

        if include_full_tree:
            if not backbone.global_options:
                backbone.global_options = {}
            backbone.global_options['include_full_tree'] = include_full_tree

        else:
            if backbone.global_options:
                del backbone.global_options['include_full_tree']

        backbone.save()

        context['backbone'] = backbone
        context['form'] = form
        context['success'] = True
        self.object = form.save()

        return self.render_to_response(context)
    

class AddMultipleBackboneTaxa(FormView):

    template_name = 'backbonetaxonomy/manage_backbone_taxa_form.html'
    form_class = AddMultipleTaxaForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.backbone = BackboneTaxonomy.objects.get(pk=self.kwargs['backbone_id'])
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_app'] = self.meta_app
        context['backbone'] = self.backbone
        context['taxaform'] = self.form_class(**self.get_form_kwargs())
        context['content_type'] = ContentType.objects.get_for_model(BackboneTaxonomy)
        return context

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)

        added = []
        existed = []
        not_found = []
        unambiguous = []
        too_short = []

        textarea_content = set([])

        names = form.cleaned_data['taxa'].split(',')

        source = form.cleaned_data['source']
        models = TaxonomyModelRouter(source)

        for name in names:

            name = name.strip()

            if len(name) > 2:

                taxa = models.TaxonTreeModel.objects.filter(taxon_latname__iexact=name)

                if len(taxa) == 1:
                    taxon = taxa[0]
                    
                    exists = self.meta_app.has_taxon(taxon)
                    if not exists:

                        exists = BackboneTaxa.objects.filter(backbonetaxonomy=self.backbone,
                                taxon_source=source, taxon_latname=taxon.taxon_latname,
                                taxon_author=taxon.taxon_author).exists()

                        if not exists:

                            lazy_taxon = LazyTaxon(instance=taxon)
                            
                            link = BackboneTaxa(
                                backbonetaxonomy = self.backbone,
                                taxon = lazy_taxon,
                            )
                            link.save()
                            
                            added.append(lazy_taxon)
                        
                    if exists:
                        existed.append(taxon)

                elif len(taxa) > 1:                            
                    unambiguous.append({'name':name, 'results':taxa})

                else:
                    not_found.append(name)
                    
            elif len(name) >0:
                too_short.append(name)


        dic = {
            'form' : form,
            'added' : added,
            'existed' : existed,
            'not_found' : not_found,
            'unambiguous' : unambiguous,
            'too_short' : too_short,
            'success' : True,
        }

        context.update(dic)
                
        return self.render_to_response(context)


# ajax post only
class AddBackboneTaxon(FormView):

    template_name = 'backbonetaxonomy/add_taxon_form.html'
    form_class = AddSingleTaxonForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.backbone = BackboneTaxonomy.objects.get(pk=self.kwargs['backbone_id'])
        self.meta_app = MetaApp.objects.get(pk=self.kwargs['meta_app_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['backbone'] = self.backbone
        context['content_type'] = ContentType.objects.get_for_model(BackboneTaxonomy)
        context['meta_app'] = self.meta_app
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super().get_form_kwargs()
        form_kwargs.update(self.get_required_form_kwargs())
        return form_kwargs

    def get_required_form_kwargs(self):

        form_kwargs = {
            'taxon_search_url' : reverse('search_taxon'),
            'descendants_choice' : True,
        }

        return form_kwargs
        

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)

        # LazyTaxon instance
        taxon = form.cleaned_data['taxon']

        exists = self.meta_app.has_taxon(taxon)

        if not exists:
            
            link = BackboneTaxa(
                backbonetaxonomy = self.backbone,
                taxon = taxon,
            )

            link.save()

        context['exists'] = exists
        context['form'] = self.form_class(**self.get_required_form_kwargs())
        context['success'] = True
        context['taxon'] = taxon

        return self.render_to_response(context)
        

# loads "really?" inside modal
class RemoveBackboneTaxon(TemplateView):

    template_name = 'backbonetaxonomy/remove_backbone_taxon.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.backbone = BackboneTaxonomy.objects.get(pk=self.kwargs['backbone_id'])
        self.models = TaxonomyModelRouter(kwargs['source'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = kwargs

        context['taxon'] = self.models.TaxonTreeModel.objects.get(name_uuid=kwargs['name_uuid'])
        context['backbone'] = self.backbone
        context['meta_app'] = MetaApp.objects.get(pk=self.kwargs['meta_app_id'])
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        backbone_id = kwargs['backbone_id']
        name_uuid = kwargs['name_uuid']

        link = BackboneTaxa.objects.filter(backbonetaxonomy=self.backbone, name_uuid=name_uuid).first()
        if link:
            link.delete()

        context['deleted'] = True

        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class SearchBackboneTaxonomy(TemplateView):
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_choices(self, request):
        
        limit = request.GET.get('limit',10)
        searchtext = request.GET.get('searchtext', None)
        language = request.GET.get('language', 'en').lower()
        
        choices = self.meta_app.search_taxon(searchtext, language, limit)
        
        return choices
        

    def get(self, request, *args, **kwargs):

        choices = self.get_choices(request)

        return HttpResponse(json.dumps(choices), content_type='application/json')


class SearchBackboneTaxonomyAndCustomTaxa(SearchBackboneTaxonomy):
    
    def get_choices(self, request):
        
        choices = super().get_choices(request)
        
        limit = request.GET.get('limit', 10)
        searchtext = request.GET.get('searchtext', None)
        language = request.GET.get('language', 'en').lower()
        
        rest_limit = limit - len(choices)
        
        if rest_limit > 0:
        
            models = TaxonomyModelRouter('taxonomy.sources.custom')
            custom_taxonomy_results = models.TaxonTreeModel.objects.filter(taxon_latname__istartswith=searchtext)[:rest_limit]
            
            for custom_taxon in custom_taxonomy_results:

                lazy_taxon = LazyTaxon(instance=custom_taxon)
                choice = lazy_taxon.as_typeahead_choice()
                choices.append(choice)
                
        return choices
    

class CollectedVernacularNames(MetaAppMixin, TemplateView):
    
    template_name = 'backbonetaxonomy/ajax/collected_vernacular_names.html'
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_taxon(self, **kwargs):
        models = TaxonomyModelRouter(kwargs['taxon_source'])
        taxon = models.TaxonNamesModel.objects.filter(name_uuid=kwargs['name_uuid']).first()
        self.lazy_taxon = LazyTaxon(instance=taxon)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        languages = self.meta_app.languages()
        all_names = self.lazy_taxon.all_vernacular_names(self.meta_app, distinct=False, languages=languages)
        context['taxon'] = self.lazy_taxon
        context['collected_vernacular_names'] = all_names
        return context
    

class ManageBackboneTaxon(MetaAppMixin, TemplateView):
    
    template_name = 'backbonetaxonomy/manage_taxon.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_taxon(self, **kwargs):
        models = TaxonomyModelRouter(kwargs['taxon_source'])
        taxon = models.TaxonTreeModel.objects.filter(name_uuid=kwargs['name_uuid']).first()
        self.lazy_taxon = LazyTaxon(instance=taxon)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        nature_guides = []
        taxon_profile = []
        
        nature_guides_content_type = ContentType.objects.get_for_model(NatureGuide)
        
        ng_meta_nodes = self.lazy_taxon.get_vernacular_meta_nodes(self.meta_app)
        for meta_node in ng_meta_nodes:
            ng_tree_occurrences = NatureGuidesTaxonTree.objects.filter(meta_node=meta_node)
            
            for ng_tree_occurrence in ng_tree_occurrences:
                nature_guides.append(ng_tree_occurrence)
        
        taxon_profiles_link = self.meta_app.get_generic_content_links(TaxonProfiles).first()
        taxon_profiles = taxon_profiles_link.generic_content
        taxon_profile = TaxonProfile.objects.filter(taxon_profiles=taxon_profiles, taxon_source=self.lazy_taxon.taxon_source, name_uuid=self.lazy_taxon.name_uuid).first()
        
        context['taxon'] = self.lazy_taxon
        context['nature_guides'] = nature_guides
        context['taxon_profiles'] = taxon_profiles
        context['taxon_profile'] = taxon_profile
        context['nature_guides_content_type'] = nature_guides_content_type
        return context
    

class AnalyzeSwapCommon:
    
    template_name = 'backbonetaxonomy/swap_taxon.html'
    form_class = SwapTaxonForm
    
    def analyze_taxon(self, from_taxon, to_taxon):
        taxon_manager = TaxonManager(self.meta_app)
        analysis = taxon_manager.get_swap_analysis(from_taxon, to_taxon)
        return analysis
    
    def get_taxon_occurrences(self, taxon):
        taxon_manager = TaxonManager(self.meta_app)
        occurrences = taxon_manager.get_verbose_occurrences(taxon)
        return occurrences
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analyzed'] = False
        context['swapped'] = False
        context['from_taxon'] = None
        context['to_taxon'] = None
        context['verbose_from_taxon_occurrences'] = []
        context['verbose_to_taxon_occurrences'] = []
        return context
    
    def get_form_valid_context_data(self, form):
        
        from_taxon = form.cleaned_data['from_taxon']
        to_taxon = form.cleaned_data['to_taxon']
        
        context = self.get_context_data(**self.kwargs)
        
        context['form'] = form
        context['from_taxon'] = from_taxon
        context['to_taxon'] = to_taxon
        context['analyzed'] = True
        context['verbose_from_taxon_occurrences'] = self.analyze_taxon(from_taxon, to_taxon)
        context['verbose_to_taxon_occurrences'] = self.get_taxon_occurrences(to_taxon)
        
        return context

    
class SwapTaxon(AnalyzeSwapCommon, MetaAppMixin, FormView):
    
    def form_valid(self, form):
        
        from_taxon = form.cleaned_data['from_taxon']
        to_taxon = form.cleaned_data['to_taxon']
        
        taxon_manager = TaxonManager(self.meta_app)
        taxon_manager.swap_taxon(from_taxon, to_taxon)
        
        context = self.get_form_valid_context_data(form)
        
        context['swapped'] = True
        
        return self.render_to_response(context)


class AnalyzeTaxon(AnalyzeSwapCommon, MetaAppMixin, FormView):
    
    def form_valid(self, form):        
        context = self.get_form_valid_context_data(form)
        return self.render_to_response(context)
    
    
class UpdateTaxonReferences(MetaAppMixin, TemplateView):
    
    template_name = 'backbonetaxonomy/update_taxon_references.html'
    
    def analyze(self):
        updater = TaxonReferencesUpdater(self.meta_app)
        result = updater.check_taxa()
        return result
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analyzed'] = False
        context['updated'] = False
        context['result'] = None
        
        if self.request.method == 'GET':
            context['result'] = self.analyze()
            context['analyzed'] = True
        
        return context
    
    def post(self, request, *args, **kwargs):
        
        updater = TaxonReferencesUpdater(self.meta_app)
        result = updater.check_taxa(update=True)
        
        context = self.get_context_data(**kwargs)
        context['result'] = result
        context['updated'] = True
        
        return self.render_to_response(context)
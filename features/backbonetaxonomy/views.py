from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView, FormView, UpdateView
from django.utils.decorators import method_decorator
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from app_kit.views import ManageGenericContent
from app_kit.models import MetaApp, MetaAppGenericContent
from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa
from app_kit.utils import get_appkit_taxon_search_url

from localcosmos_server.decorators import ajax_required
from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from .forms import (AddMultipleTaxaForm, ManageFulltreeForm, SearchTaxonomicBackboneForm)


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

    def get(self, request, *args, **kwargs):

        meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])

        limit = request.GET.get('limit',10)
        searchtext = request.GET.get('searchtext', None)
        language = request.GET.get('language', 'en').lower()
        
        choices = meta_app.search_taxon(searchtext, language, limit)

        return HttpResponse(json.dumps(choices), content_type='application/json')

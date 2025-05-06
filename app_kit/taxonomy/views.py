from django.http import HttpResponse
from django.utils.translation import gettext as _

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from taxonomy.models import TaxonomyModelRouter, MetaVernacularNames
from taxonomy.forms import ManageMetaVernacularNameForm

from django.views.generic import TemplateView, FormView

from taxonomy.lazy import LazyTaxon
from .TaxonSearch import TaxonSearch

from .utils import get_lazy_taxon_from_name_uuid

from django.db.models.functions import Length

from app_kit.models import MetaApp
from app_kit.view_mixins import MetaAppMixin, MetaAppFormLanguageMixin

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator


from localcosmos_server.generic_views import AjaxDeleteView

import json


class SearchTaxon(FormView):

    form_class = AddSingleTaxonForm

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', 10)
        searchtext = request.GET.get('searchtext', None)
        language = request.GET.get('language', 'en').lower()
        source = request.GET['taxon_source']

        search = TaxonSearch(source, searchtext, language, **{'limit':limit})

        choices = search.get_choices_for_typeahead()

        return HttpResponse(json.dumps(choices), content_type='application/json')

'''
    Displaying a TreeView
    - DOES NOT WORK ON STANDALONE INSTALLS
    - works with all taxonomic sources
    - start with root taxa
    - make each node expandable
'''
class TaxonTreeView(TemplateView):

    template_name = 'taxonomy/taxontreeview.html'
    tree_entry_template_name = 'taxonomy/treeview_entry.html' # does not exist anymore, needs to be rewritten

    # load_custom_taxon_children is an ajax view (subclass of this one) that does not need app
    load_app_bar = True
    meta_app = None

    def dispatch(self, request, *args, **kwargs):
        self.models = self.get_taxonomy(**kwargs)
        self.taxon = None
        if 'name_uuid' in kwargs:
            self.taxon = self.models.TaxonTreeModel.objects.get(name_uuid=kwargs['name_uuid'])

        # App is not available on standalone installs, but the app taxonomy is
        # importing App outside a class would result in an error on standalone installs
        if self.load_app_bar == True:
            self.meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
            
        return super().dispatch(request, *args, **kwargs)

    def get_root_taxa(self):
        return self.models.TaxonTreeModel.objects.filter(is_root_taxon=True)

    def get_taxa(self):
        if self.taxon:
            children_nuid_length = len(self.taxon.taxon_nuid) + 3
            taxa = self.models.TaxonTreeModel.objects.annotate(nuid_len=Length('taxon_nuid')).filter(
                taxon_nuid__startswith=self.taxon.taxon_nuid, nuid_len=children_nuid_length)
            
        else:
            taxa = self.get_root_taxa()

        return taxa

    def get_taxonomy(self, **kwargs):
        return TaxonomyModelRouter(kwargs['source'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['language'] = kwargs['language']
        context['taxa'] = self.get_taxa()
        context['parent_taxon'] = self.taxon
        context['tree_entry_template'] = self.tree_entry_template_name
        context['meta_app'] = self.meta_app
        return context
        

class ManageMetaVernacularName(MetaAppFormLanguageMixin, FormView):
    
    template_name = 'taxonomy/ajax/manage_meta_vernacular_name.html'
    form_class = ManageMetaVernacularNameForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon_and_name(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_taxon_and_name(self, **kwargs):
        self.meta_vernacular_name = None
        name_id = kwargs.get('meta_vernacular_name_id', None)
        
        if name_id:
            self.meta_vernacular_name = MetaVernacularNames.objects.get(pk=name_id)
            taxon_source = self.meta_vernacular_name.taxon_source
            name_uuid = self.meta_vernacular_name.name_uuid
        else:
            taxon_source = kwargs['taxon_source']
            name_uuid = kwargs['name_uuid']
        
        self.lazy_taxon = get_lazy_taxon_from_name_uuid(taxon_source, name_uuid)


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.lazy_taxon, self.meta_vernacular_name,
                          **self.get_form_kwargs())
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon'] = self.lazy_taxon
        context['meta_vernacular_name'] = self.meta_vernacular_name
        context['success'] = False
        return context
    
    def get_initial(self):
        initial = super().get_initial()
        if self.meta_vernacular_name:
            initial['name'] = self.meta_vernacular_name.name
            initial['preferred'] = self.meta_vernacular_name.preferred
        return initial
    
    def form_valid(self, form):
        
        if not self.meta_vernacular_name:
            self.meta_vernacular_name = MetaVernacularNames(
                taxon_source = self.lazy_taxon.taxon_source,
                taxon_latname = self.lazy_taxon.taxon_latname,
                taxon_author = self.lazy_taxon.taxon_author,
                name_uuid = self.lazy_taxon.name_uuid,
                taxon_nuid = self.lazy_taxon.taxon_nuid,
            )
            
        self.meta_vernacular_name.language = form.cleaned_data['input_language']
        self.meta_vernacular_name.name = form.cleaned_data['name']
        self.meta_vernacular_name.preferred = form.cleaned_data.get('preferred', False)
        
        self.meta_vernacular_name.save()
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        
        return self.render_to_response(context)
    

class DeleteMetaVernacularName(AjaxDeleteView):

    model = MetaVernacularNames
    template_name = 'taxonomy/ajax/delete_meta_vernacular_name.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_app'] = MetaApp.objects.get(pk=self.kwargs['meta_app_id'])
        context['taxon'] = self.object
        return context
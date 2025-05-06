'''
    CUSTOM TAXA
    - requires taxonomy.sources.custom
    - these view have to live within app_kit context as they require an App
    - the standalone uses taxonomy as a service - TaaS for querying custom taxa etc
    - alternatively fills its own db by querying a service - on demand
'''
from django.views.generic import FormView

from .forms import ManageCustomTaxonForm, MoveCustomTaxonForm

from taxonomy.models import TaxonomyModelRouter
from taxonomy.utils import NuidManager
from taxonomy.lazy import LazyTaxon

from django.utils.decorators import method_decorator
from localcosmos_server.decorators import ajax_required


custom_taxon_models = TaxonomyModelRouter('taxonomy.sources.custom')

from django.db.models import CharField
from django.db.models.functions import Length
CharField.register_lookup(Length, 'length')


class ManageCustomTaxon(FormView):

    template_name = 'custom_taxonomy/manage_custom_taxon.html'

    form_class = ManageCustomTaxonForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.taxon = None
        self.parent_taxon = None
        self.locale = None
        self.language = kwargs['language']
        
        if 'name_uuid' in kwargs:
            self.taxon = custom_taxon_models.TaxonTreeModel.objects.get(name_uuid=kwargs['name_uuid'])

            self.locale = custom_taxon_models.TaxonLocaleModel.objects.filter(
                taxon_id=str(self.taxon.name_uuid), language=self.language).first()

            if not self.taxon.is_root_taxon:
                self.parent_taxon = custom_taxon_models.TaxonTreeModel.objects.get(
                    taxon_nuid=str(self.taxon.taxon_nuid)[:-3])

        if self.parent_taxon == None and 'parent_name_uuid' in kwargs:
            self.parent_taxon = custom_taxon_models.TaxonTreeModel.objects.get(
                name_uuid=kwargs['parent_name_uuid'])
        
        return super().dispatch(request, *args, **kwargs)


    def get_initial(self):

        if self.taxon is not None:
            
            initial = {
                'name_uuid' : self.taxon.name_uuid,
                'taxon_latname' : self.taxon.taxon_latname,
                'taxon_author' : self.taxon.taxon_author,
                'rank' : self.taxon.rank,
            }

            if self.locale:
                initial['name'] = self.locale.name
                    
        else:
            initial = {}

        if self.parent_taxon is not None:
            initial['parent_name_uuid'] = self.parent_taxon.name_uuid
        return initial


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['language'] = self.language
        context['taxon'] = self.taxon
        context['parent_taxon'] = self.parent_taxon
        return context

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['language'] = self.language
        return form_kwargs

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)
        
        created = False
        
        if self.taxon is None:
            created = True
            
            extra_fields = {
                'rank' : form.cleaned_data.get('rank', None),
            }

            if not self.parent_taxon:
                extra_fields['is_root_taxon'] = True

            else:
                extra_fields['parent'] = self.parent_taxon
                
            self.taxon = custom_taxon_models.TaxonTreeModel.objects.create(
                form.cleaned_data['taxon_latname'],
                form.cleaned_data.get('taxon_author', None),
                **extra_fields
            )

        else:
            self.taxon.taxon_latname = form.cleaned_data['taxon_latname']
            self.taxon.rank = form.cleaned_data.get('rank', None)
            self.taxon.taxon_author = form.cleaned_data.get('taxon_author', None)

            self.taxon.save()


        if self.locale is None:
            self.locale = custom_taxon_models.TaxonLocaleModel.objects.create(
                self.taxon, form.cleaned_data['name'], form.cleaned_data['input_language'],
                preferred = True,
            )

        else:
            self.locale.name = form.cleaned_data['name']
            self.locale.save()

        context['form'] = form
        context['success'] = True
        context['created'] = created
        context['taxon'] = LazyTaxon(instance=self.taxon)
        return self.render_to_response(context)


from localcosmos_server.generic_views import AjaxDeleteView
class DeleteTaxon(AjaxDeleteView):
    model = custom_taxon_models.TaxonTreeModel

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)
        context['deleted_object_id'] = self.object.pk
        context['deleted'] = True

        taxon_with_descendants = self.model.objects.filter(taxon_nuid__startswith=self.object.taxon_nuid).order_by('-taxon_nuid')

        for taxon in taxon_with_descendants:
            taxon.delete()
            
        return self.render_to_response(context)


from taxonomy.views import TaxonTreeView
'''
    - create the three root taxa (Animalia, Plantae, Fungi) if not yet present
'''
class ManageCustomTaxonTree(TaxonTreeView):

    template_name = 'custom_taxonomy/manage_custom_taxonomy.html'
    tree_entry_template_name = 'custom_taxonomy/manage_tree_entry.html'

    initial_root_taxa = ['Animalia','Fungi','Plantae']

    def create_initial_root_taxa(self):

        taxon_author = self.request.user.username

        for taxon_latname in self.initial_root_taxa:

            # taxon_latname, taxon_author
            self.models.TaxonTreeModel.objects.create(taxon_latname, taxon_author, is_root_taxon=True, rank='kingdom')


    def get_root_taxa(self):
        root_taxa = self.models.TaxonTreeModel.objects.filter(is_root_taxon=True)

        if not root_taxa:
            self.create_initial_root_taxa()
            root_taxa = self.models.TaxonTreeModel.objects.filter(is_root_taxon=True)

        for taxon in root_taxa:
            if taxon.taxon_latname in self.initial_root_taxa:
                taxon.is_locked = True

        return root_taxa

    def get_taxonomy(self, **kwargs):
        return TaxonomyModelRouter('taxonomy.sources.custom')


class ManageCustomTaxonChildren(ManageCustomTaxonTree):
    template_name = 'taxonomy/treeview_children.html'
    load_app_bar = False

    

'''
    moving has to update across lazy taxa
    moving is currently disabled because of nuid problems when moving a taxon
    moving a taxon would require updating all nuids of all descendant taxa across all ModelWithTaxon subclasses
'''
from taxonomy.utils import get_subclasses
from localcosmos_server.taxonomy.generic import ModelWithRequiredTaxon, ModelWithTaxon


class MoveCustomTaxonTreeEntry(FormView):

    template_name = 'custom_taxonomy/move_custom_taxon.html'
    form_class = MoveCustomTaxonForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.taxon = custom_taxon_models.TaxonTreeModel.objects.get(name_uuid=kwargs['name_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon'] = self.taxon
        return context


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.taxon, **self.get_form_kwargs())


    def update_nuids(self, taxon, Subclass):
        taxa = Subclass.objects.filter(taxon_source='taxonomy.sources.custom', name_uuid=taxon.name_uuid)
        taxa.update(taxon_nuid=taxon.taxon_nuid)

    def update_lazy_taxa(self, taxon):
        for Subclass in get_subclasses(ModelWithRequiredTaxon):
            self.update_nuids(taxon, Subclass)

        for Subclass in get_subclasses(ModelWithTaxon):
            self.update_nuids(taxon, Subclass)
    
    
    def get_new_taxon_nuid(self, new_parent):
        
        nuid_manager = NuidManager()
        
        new_siblings = custom_taxon_models.TaxonTreeModel.objects.filter(
            parent=new_parent).order_by('taxon_nuid')
        
        last_sibling = new_siblings.last()
        
        if last_sibling:
            new_nuid = nuid_manager.next_nuid(last_sibling.taxon_nuid)
        else:
            new_nuid = '{0}001'.format(new_parent.taxon_nuid)
        
        return new_nuid
        

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)

        # move the taxon, use the form taxon as this has been validated against the new parent taxon
        new_parent_lazy_taxon = form.cleaned_data['new_parent_taxon']
        new_parent_taxon = custom_taxon_models.TaxonTreeModel.objects.get(name_uuid=new_parent_lazy_taxon.name_uuid)

        old_taxon_nuid = self.taxon.taxon_nuid
        new_taxon_nuid = self.get_new_taxon_nuid(new_parent_taxon)
        
        self.taxon.parent = new_parent_taxon
        self.taxon.taxon_nuid = new_taxon_nuid
        
        self.taxon.save()
        
        # get all descendants
        for descendant_taxon in custom_taxon_models.TaxonTreeModel.objects.filter(taxon_nuid__startswith=old_taxon_nuid):

            descendant_taxon.taxon_nuid = descendant_taxon.taxon_nuid.replace(
                old_taxon_nuid, new_taxon_nuid, 1)
            descendant_taxon.save()

            # update all occurrences across database
            self.update_lazy_taxa(descendant_taxon)

        context['new_parent_taxon'] = new_parent_taxon
        context['success'] = True
        context['form'] = form
        return self.render_to_response(context)

from django.conf import settings
from django.views.generic import TemplateView, FormView
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.contrib.contenttypes.models import ContentType

from django.urls import reverse
from django.http import JsonResponse

from .forms import TaxonProfilesOptionsForm, ManageTaxonTextTypeForm, ManageTaxonTextsForm
from .models import TaxonTextType, TaxonText, TaxonProfiles, TaxonProfile

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppFormLanguageMixin, MetaAppMixin
from app_kit.models import ContentImage

from app_kit.features.nature_guides.models import MetaNode, NatureGuidesTaxonTree, NodeFilterSpace

from localcosmos_server.decorators import ajax_required

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon



def get_taxon(taxon_source, name_uuid):
    models = TaxonomyModelRouter(taxon_source)

    # use the names model to support synonyms
    if taxon_source == 'taxonomy.sources.custom':
        taxon = models.TaxonTreeModel.objects.get(name_uuid=name_uuid)
    else:    
        taxon = models.TaxonNamesModel.objects.get(name_uuid=name_uuid)

    return taxon
    
'''
    profiles can occur in NatureGuides or IdentificationKeys, check these in the validation method
'''
class ManageTaxonProfiles(ManageGenericContent):

    options_form_class = TaxonProfilesOptionsForm
    template_name = 'taxon_profiles/manage_taxon_profiles.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxa'] = self.generic_content.collected_taxa()

        form_kwargs = {
            'taxon_search_url': reverse('search_backbonetaxonomy', kwargs={'meta_app_id':self.meta_app.id}),
            'fixed_taxon_source' : '__all__'
        }
        
        context['searchbackboneform'] = AddSingleTaxonForm(**form_kwargs)
        return context


'''
    since the "copy tree branches" requirement has been implemented (AWI), name duplicates are possible
    -> lookup of profiles can only be done by name_uuid
'''
class ManageTaxonProfile(MetaAppFormLanguageMixin, FormView):

    form_class = ManageTaxonTextsForm
    template_name = 'taxon_profiles/manage_taxon_profile.html'
    ajax_template_name = 'taxon_profiles/ajax/manage_taxon_profile_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.set_taxon(request, **kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_taxon(self, request, **kwargs):
        
        self.taxon_profiles =  TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])

        taxon_source = kwargs['taxon_source']
        name_uuid = kwargs['name_uuid']

        taxon = get_taxon(taxon_source, name_uuid)

        self.taxon = LazyTaxon(instance=taxon)

        taxon_profile = TaxonProfile.objects.filter(taxon_profiles=self.taxon_profiles,
                    taxon_source=self.taxon.taxon_source, name_uuid=name_uuid).first()


        if not taxon_profile:
            taxon_profile = TaxonProfile(
                taxon_profiles = self.taxon_profiles,
                taxon=self.taxon,
            )
            taxon_profile.save()
            

        self.taxon_profile = taxon_profile
            

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.template_name = self.ajax_template_name
            

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()

        return form_class(self.taxon_profiles, self.taxon_profile, **self.get_form_kwargs())


    def get_meta_node_names(self):

        meta_node_names = MetaNode.objects.filter(taxon_source=self.taxon.taxon_source,
                taxon_latname=self.taxon.taxon_latname,
                taxon_author=self.taxon.taxon_author).values_list('name', flat=True)

        return meta_node_names


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon'] = self.taxon
        context['taxon_profile'] = self.taxon_profile
        context['content_type'] = ContentType.objects.get_for_model(self.taxon_profile)
        context['node_names'] = self.get_meta_node_names()
        context['taxon_profiles'] = self.taxon_profiles
        context['generic_content'] = self.taxon_profiles
        context['text_types'] = TaxonTextType.objects.all().exists()
        context['show_text_length_badges'] = settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True
        return context


    def form_valid(self, form):

        # iterate over all text types and save them
        for field_name, value in form.cleaned_data.items():

            if field_name in form.short_text_fields or field_name in form.long_text_fields:

                taxon_text_type = form.text_type_map[field_name]

                taxon_text, created = TaxonText.objects.get_or_create(taxon_profile=self.taxon_profile,
                                                                      taxon_text_type=taxon_text_type)

                if field_name in form.short_text_fields:
                    taxon_text.text = value

                elif  field_name in form.long_text_fields:
                    taxon_text.long_text = value

                taxon_text.save()
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['saved'] = True
        return self.render_to_response(context)


class GetManageOrCreateTaxonProfileURL(MetaAppMixin, TemplateView):

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon(request, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_taxon(self, request, **kwargs):
        taxon_source = request.GET['taxon_source']
        models = TaxonomyModelRouter(taxon_source)

        # maye use latname& author in the future - what happens to name_uuid if taxonDB gets updated?
        #taxon_latname = request.GET['taxon_latname']
        #taxon_author = request.GET['taxon_author']

        name_uuid = request.GET['name_uuid']
        
        #taxon = models.TaxonTreeModel.objects.get(taxon_latname=taxon_latname, taxon_author=taxon_author)
        taxon = get_taxon(taxon_source, name_uuid)

        self.taxon = LazyTaxon(instance=taxon)

        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])


    def get(self, request, *args, **kwargs):

        url_kwargs = {
            'meta_app_id':self.meta_app.id,
            'taxon_profiles_id' : self.taxon_profiles.id,
            'taxon_source' : self.taxon.taxon_source,
            'name_uuid' : self.taxon.name_uuid,
        }
        
        url = reverse('manage_taxon_profile', kwargs=url_kwargs)

        data = {
            'url' : url,
        }
        
        return JsonResponse(data)

    

class ManageTaxonTextType(MetaAppFormLanguageMixin, FormView):

    template_name = 'taxon_profiles/ajax/manage_text_type.html'
    form_class = ManageTaxonTextTypeForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon_text_type(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_taxon_text_type(self, **kwargs):

        # get the taxon
        taxon_source = kwargs['taxon_source']
        name_uuid = kwargs['name_uuid']
        taxon = get_taxon(taxon_source, name_uuid)
        self.taxon = LazyTaxon(instance=taxon)
        
        self.taxon_profiles =  TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])

        self.taxon_text_type = None
        if 'taxon_text_type_id' in kwargs:
            self.taxon_text_type = TaxonTextType.objects.get(pk=kwargs['taxon_text_type_id'])
        

    def get_initial(self):
        initial = super().get_initial()
        initial['taxon_profiles'] = self.taxon_profiles
        return initial


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()

        return form_class(instance=self.taxon_text_type, **self.get_form_kwargs())


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_text_type'] = self.taxon_text_type
        context['taxon_profiles'] = self.taxon_profiles
        context['taxon'] = self.taxon
        return context
    

    def form_valid(self, form):

        created = True
        if self.taxon_text_type:
            created = False

        self.taxon_text_type = form.save(commit=False)
        self.taxon_text_type.save()
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        context['created'] = created

        return self.render_to_response(context)


from localcosmos_server.generic_views import AjaxDeleteView
class DeleteTaxonTextType(AjaxDeleteView):

    model = TaxonTextType
    template_name = 'taxon_profiles/ajax/delete_taxon_text_type.html'


class ManageTaxonTextTypesOrder(TemplateView):

    template_name = 'taxon_profiles/ajax/manage_text_types_order.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon_profiles(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_taxon_profiles(self, **kwargs):
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['text_types'] = TaxonTextType.objects.filter(taxon_profiles=self.taxon_profiles)
        context['text_types_content_type'] = ContentType.objects.get_for_model(TaxonTextType)
        return context


class CollectTaxonImages(MetaAppFormLanguageMixin, TemplateView):

    template_name = 'taxon_profiles/ajax/collected_taxon_images.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_taxon(self, **kwargs):
        self.taxon_profile = TaxonProfile.objects.get(pk=kwargs['pk'])
        taxon_source = kwargs['taxon_source']
        name_uuid = kwargs['name_uuid']
        taxon = get_taxon(taxon_source, name_uuid)
        self.taxon = LazyTaxon(instance=taxon)


    def get_taxon_profile_images(self):
        taxon_profile_ctype = ContentType.objects.get_for_model(self.taxon_profile)
        images = ContentImage.objects.filter(content_type=taxon_profile_ctype,
                                             object_id=self.taxon_profile.id).order_by('position')

        return images

    def get_taxon_images(self, exclude=[]):
        images = ContentImage.objects.filter(image_store__taxon_source=self.taxon.taxon_source,
                            image_store__taxon_latname=self.taxon.taxon_latname).exclude(pk__in=exclude)

        return images
    
    # images can be on MetNode or NatureGuidesTaxonTree
    def get_nature_guide_images(self, exclude=[]):
        
        meta_nodes = MetaNode.objects.filter(taxon_source=self.taxon.taxon_source,
                                taxon_latname=self.taxon.taxon_latname, taxon_author=self.taxon.taxon_author)

        nature_guide_images = []

        if meta_nodes:

            meta_node_ids = meta_nodes.values_list('id', flat=True)

            meta_node_content_type = ContentType.objects.get_for_model(MetaNode)
            meta_node_images = ContentImage.objects.filter(content_type=meta_node_content_type,
                                            object_id__in=meta_node_ids).exclude(pk__in=exclude)
            
            exclude += list(meta_node_images.values_list('id', flat=True))
            nature_guide_images += list(meta_node_images)

        
        nodes = NatureGuidesTaxonTree.objects.filter(meta_node__taxon_source=self.taxon.taxon_source,
            meta_node__taxon_latname=self.taxon.taxon_latname,
            meta_node__taxon_author=self.taxon.taxon_author)

        if nodes:

            node_ids = nodes.values_list('id', flat=True)

            node_content_type = ContentType.objects.get_for_model(NatureGuidesTaxonTree)
            node_images = ContentImage.objects.filter(content_type=node_content_type,
                                            object_id__in=node_ids).exclude(pk__in=exclude)
            
            nature_guide_images += list(node_images)
            

        return nature_guide_images
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        taxon_profile_images = self.get_taxon_profile_images()
        context['taxon_profile_images'] = taxon_profile_images

        exclude = list(set(list(taxon_profile_images.values_list('pk', flat=True))))
        node_images = self.get_nature_guide_images(exclude=exclude)
        context['node_images'] = node_images

        exclude += list(set([image.pk for image in node_images]))
        taxon_images = self.get_taxon_images(exclude=exclude)
        context['taxon_images'] = taxon_images


        context['taxon_profile'] = self.taxon_profile
        context['taxon'] = self.taxon

        context['content_image_ctype'] = ContentType.objects.get_for_model(ContentImage)
        return context


class CollectTaxonTraits(TemplateView):

    template_name = 'taxon_profiles/ajax/collected_taxon_traits.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_taxon(self, **kwargs):
        taxon_source = kwargs['taxon_source']
        name_uuid = kwargs['name_uuid']

        taxon = get_taxon(taxon_source, name_uuid)

        self.taxon = LazyTaxon(instance=taxon)


    def get_taxon_traits(self):

        spaces = []
        
        nodes = NatureGuidesTaxonTree.objects.filter(meta_node__taxon_source=self.taxon.taxon_source,
                meta_node__taxon_latname=self.taxon.taxon_latname,
                meta_node__taxon_author=self.taxon.taxon_author)
        
        node_spaces = NodeFilterSpace.objects.filter(node__in=nodes)

        spaces += list(node_spaces)

        for node in nodes:

            parent_node_nuids = []
            current_nuid = node.taxon_nuid
            while len(current_nuid) >= 9:
                current_nuid = current_nuid[:-3]
                parent_node_nuids.append(current_nuid)

            parent_nodes = NatureGuidesTaxonTree.objects.filter(taxon_nuid__in=parent_node_nuids)
            parent_node_spaces = NodeFilterSpace.objects.filter(node__in=parent_nodes)
            spaces += list(parent_node_spaces)
        
        return spaces


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_traits'] = self.get_taxon_traits()
        return context


from app_kit.views import ManageContentImageWithText, DeleteContentImage
class ManageTaxonProfileImage(ManageContentImageWithText):
    template_name = 'taxon_profiles/ajax/manage_taxon_profile_image.html'


class DeleteTaxonProfileImage(DeleteContentImage):
    template_name = 'taxon_profiles/ajax/delete_taxon_profile_image.html'
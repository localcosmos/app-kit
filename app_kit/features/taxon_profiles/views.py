from django.conf import settings
from django.views.generic import TemplateView, FormView
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.contrib.contenttypes.models import ContentType

from django.urls import reverse
from django.http import JsonResponse

from .forms import (TaxonProfilesOptionsForm, ManageTaxonTextTypeForm, ManageTaxonTextsForm,
                    ManageTaxonProfilesNavigationEntryForm, AddTaxonProfilesNavigationEntryTaxonForm,
                    TaxonProfileStatusForm, ManageTaxonTextTypeCategoryForm)

from .models import (TaxonTextType, TaxonText, TaxonProfiles, TaxonProfile, TaxonProfilesNavigation,
                     TaxonProfilesNavigationEntry, TaxonProfilesNavigationEntryTaxa, TaxonTextTypeCategory)

from app_kit.views import (ManageGenericContent, ManageContentImage, ManageContentImageWithText, DeleteContentImage,
                           ManageObjectOrder)
from app_kit.view_mixins import MetaAppFormLanguageMixin, MetaAppMixin
from app_kit.models import ContentImage
from app_kit.forms import GenericContentStatusForm

from app_kit.features.nature_guides.models import (MetaNode, NatureGuidesTaxonTree, NodeFilterSpace, NatureGuide)
from app_kit.features.backbonetaxonomy.models import BackboneTaxa, BackboneTaxonomy

from localcosmos_server.decorators import ajax_required

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon

from localcosmos_server.generic_views import AjaxDeleteView


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
class GetNatureGuideTaxaMixin:

    def get_nature_guide_taxon_results(self, nature_guide):
        taxon_results_pks = MetaNode.objects.filter(nature_guide=nature_guide,
            node_type='result', taxon_latname__isnull=False).distinct('name_uuid').values_list('pk', flat=True)
            
        results = MetaNode.objects.filter(pk__in=taxon_results_pks).order_by('name')

        return results
    
    def get_nature_guide_non_taxon_results(self, nature_guide):
        non_taxon_results = MetaNode.objects.filter(nature_guide=nature_guide,
            node_type='result', taxon_latname__isnull=True).order_by('name')

        return non_taxon_results


class ManageTaxonProfiles(GetNatureGuideTaxaMixin, ManageGenericContent):

    options_form_class = TaxonProfilesOptionsForm
    template_name = 'taxon_profiles/manage_taxon_profiles.html'

    page_template_name = 'taxon_profiles/ajax/non_nature_guide_taxonlist.html'

    def dispatch(self, request, *args, **kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            self.template_name = self.page_template_name
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nature_guide_results = []
        nature_guide_links = self.meta_app.get_generic_content_links(NatureGuide)

        nature_guide_taxa_name_uuids = []

        for nature_guide_link in nature_guide_links:
            nature_guide = nature_guide_link.generic_content

            results = self.get_nature_guide_taxon_results(nature_guide)
            
            non_taxon_results = self.get_nature_guide_non_taxon_results(nature_guide)

            entry = {
                'nature_guide': nature_guide,
                'results': results,
                'non_taxon_results': non_taxon_results,
            }

            for meta_node in results:
                if meta_node.taxon:
                    nature_guide_taxa_name_uuids.append(meta_node.name_uuid)
                else:
                    fallback_taxa = NatureGuidesTaxonTree.objects.filter(meta_node=meta_node, nature_guide=nature_guide)
                    for fallback_taxon in fallback_taxa:
                        nature_guide_taxa_name_uuids.append(fallback_taxon.name_uuid)

            nature_guide_results.append(entry)

        non_nature_guide_taxon_profiles = TaxonProfile.objects.filter(taxon_profiles=self.generic_content).exclude(
                name_uuid__in=nature_guide_taxa_name_uuids).order_by('taxon_latname')
        
        backbonetaxonomy_link = self.meta_app.get_generic_content_links(BackboneTaxonomy)[0]
        backbonetaxonomy = backbonetaxonomy_link.generic_content
        backbone_taxa_name_uuids = BackboneTaxa.objects.filter(
            backbonetaxonomy=backbonetaxonomy).values_list('name_uuid', flat=True)
        backbone_taxa_profiles_name_uuids = TaxonProfile.objects.filter(
            taxon_profiles=self.generic_content,
            name_uuid__in=backbone_taxa_name_uuids).values_list('name_uuid', flat=True)
        backbone_taxa_noprofile = BackboneTaxa.objects.filter(backbonetaxonomy=backbonetaxonomy).exclude(
            name_uuid__in=backbone_taxa_profiles_name_uuids).order_by('-pk')
        
        uses_taxon_profiles_navigation = self.generic_content.get_option(self.meta_app, 'enable_taxonomic_navigation')
        taxon_profiles_navigation = TaxonProfilesNavigation.objects.filter(
            taxon_profiles=self.generic_content).first()

        context['nature_guide_results'] = nature_guide_results
        context['non_nature_guide_taxon_profiles'] = non_nature_guide_taxon_profiles
        context['taxa'] = self.generic_content.collected_taxa()
        context['backbone_taxa_noprofile'] = backbone_taxa_noprofile
        context['uses_taxon_profiles_navigation'] = uses_taxon_profiles_navigation
        context['taxon_profiles_navigation'] = taxon_profiles_navigation

        form_kwargs = {
            'taxon_search_url': reverse('search_backbonetaxonomy_and_custom_taxa', kwargs={'meta_app_id':self.meta_app.id}),
            'fixed_taxon_source' : '__all__',
        }
        
        context['searchbackboneform'] = AddSingleTaxonForm(**form_kwargs)
        return context


class NatureGuideTaxonProfilePage(GetNatureGuideTaxaMixin, ManageGenericContent):
    template_name = 'taxon_profiles/ajax/nature_guide_taxonlist.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nature_guide = NatureGuide.objects.get(pk=kwargs['nature_guide_id'])

        if kwargs['list_type'] == 'results':
            results = self.get_nature_guide_taxon_results(nature_guide)
        else:
            results = self.get_nature_guide_non_taxon_results(nature_guide)

        context['nature_guide'] = nature_guide
        context['results'] = results
 

        url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'content_type_id': kwargs['content_type_id'],
            'object_id': self.generic_content.id,
            'nature_guide_id': kwargs['nature_guide_id'],
            'list_type': kwargs['list_type']
        }
        context['pagination_url'] = reverse('get_nature_guide_taxonprofile_page', kwargs=url_kwargs)

        return context

class CreateTaxonProfileMixin:

    def create_taxon_profile(self, taxon_profiles, taxon):

        '''
        taxon_profile = TaxonProfile.objects.filter(taxon_profiles=taxon_profiles,
            taxon_source=taxon.taxon_source, taxon_latname=taxon.taxon_latname,
            taxon_author=taxon.taxon_author).first()
        '''
        taxon_profile = TaxonProfile.objects.filter(taxon_profiles=taxon_profiles,
            taxon_source=taxon.taxon_source, name_uuid=taxon.name_uuid).first()

        if not taxon_profile:
            taxon_profile = TaxonProfile(
                taxon_profiles=taxon_profiles,
                taxon=taxon,
            )
            taxon_profile.save()

        return taxon_profile


class CreateTaxonProfile(CreateTaxonProfileMixin, MetaAppMixin, TemplateView):
    template_name = 'taxon_profiles/ajax/create_taxon_profile.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_taxon(self, **kwargs):
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])

        taxon_source = kwargs['taxon_source']
        name_uuid = kwargs['name_uuid']
        
        #taxon = models.TaxonTreeModel.objects.get(taxon_latname=taxon_latname, taxon_author=taxon_author)
        taxon = get_taxon(taxon_source, name_uuid)

        self.taxon = LazyTaxon(instance=taxon)

        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_profiles'] = self.taxon_profiles
        context['taxon'] = self.taxon
        context['success'] = False
        return context
    
    def post(self, request, *args, **kwargs):
        
        taxon_profile = self.create_taxon_profile(self.taxon_profiles, self.taxon)

        context = self.get_context_data(**kwargs)
        context['taxon_profile'] = taxon_profile
        context['success'] = True

        return self.render_to_response(context)


'''
    since the "copy tree branches" requirement has been implemented (AWI), name duplicates are possible
    -> lookup of profiles can only be done by name_uuid
'''
class ManageTaxonProfile(CreateTaxonProfileMixin, MetaAppFormLanguageMixin, FormView):

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

        taxon_profile = TaxonProfile.objects.get(taxon_profiles=self.taxon_profiles,
                                                 taxon_source=taxon_source, name_uuid=name_uuid)

        # the taxcon might not exist anymore in the source
        #taxon = get_taxon(taxon_source, name_uuid)

        self.taxon = LazyTaxon(instance=taxon_profile)

        # unique constraing covers source, latname authot
        #taxon_profile = TaxonProfile.objects.filter(taxon_profiles=self.taxon_profiles,
        #            taxon_source=self.taxon.taxon_source, name_uuid=name_uuid).first()

        
        self.taxon_profile = self.create_taxon_profile(self.taxon_profiles, self.taxon)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.template_name = self.ajax_template_name
    
    def get_initial(self):
        initial = super().get_initial()
        initial['short_profile'] = self.taxon_profile.short_profile
        return initial
    

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()

        return form_class(self.taxon_profiles, self.taxon_profile, **self.get_form_kwargs())


    def get_navigation_branches(self):
        branches = []
        navigation = TaxonProfilesNavigation.objects.filter(taxon_profiles=self.taxon_profiles).first()
        
        if navigation:
            terminal_nodes = navigation.get_terminal_nodes()
            
            for navigation_entry in terminal_nodes:
                
                matches = False
                
                for navigation_entry_taxon in navigation_entry.taxa:
                    if navigation_entry_taxon.taxon_source == self.taxon.taxon_source and self.taxon.taxon_nuid.startswith(navigation_entry_taxon.taxon_nuid):
                        matches = True
                        break
                    
                if matches == True:
                    branches.append(navigation_entry.branch)
                
        return branches


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nature_guides = []
        if self.taxon_profile.taxon_source == 'app_kit.features.nature_guides':
            tree_entry = NatureGuidesTaxonTree.objects.filter(name_uuid=self.taxon_profile.name_uuid).first()
            if tree_entry:
                nature_guides = [tree_entry.nature_guide]
        else:
            possible_nature_guide_ids = self.meta_app.get_generic_content_links(NatureGuide).values_list('object_id', flat=True)
            nature_guide_ids = MetaNode.objects.filter(name_uuid=self.taxon_profile.name_uuid,
                nature_guide_id__in=possible_nature_guide_ids).values_list('nature_guide', flat=True).distinct()
            nature_guides = NatureGuide.objects.filter(pk__in=nature_guide_ids)

        context['nature_guides'] = nature_guides
        models = TaxonomyModelRouter(self.taxon_profile.taxon_source)
        context['taxon_tree_model'] = models.TaxonTreeModel._meta.verbose_name

        context['taxon'] = self.taxon
        context['taxon_profile'] = self.taxon_profile
        context['vernacular_name_from_nature_guides'] = self.taxon.get_primary_locale_vernacular_name_from_nature_guides(
            self.meta_app)
        context['content_type'] = ContentType.objects.get_for_model(self.taxon_profile)
        context['taxon_profiles'] = self.taxon_profiles
        context['generic_content'] = self.taxon_profiles
        context['text_types'] = TaxonTextType.objects.all().exists()
        context['show_text_length_badges'] = settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True
        
        context['taxonomic_branch'] = self.taxon.get_taxonomic_branch()
        
        context['navigation_branches'] = self.get_navigation_branches()

        # show possible duplicates
        possible_duplicates = TaxonProfile.objects.filter(taxon_profiles=self.taxon_profiles,
            taxon_latname=self.taxon_profile.taxon_latname).exclude(pk=self.taxon_profile.pk)
        context['possible_duplicates'] = possible_duplicates
        
        context['category_content_type'] = ContentType.objects.get_for_model(TaxonTextTypeCategory)
        context['text_type_content_type'] = ContentType.objects.get_for_model(TaxonTextType)
        
        context['content_image_ctype'] = ContentType.objects.get_for_model(ContentImage)
        return context


    def form_valid(self, form):
        
        short_profile = form.cleaned_data.get('short_profile', None)

        self.taxon_profile.short_profile = short_profile
        self.taxon_profile.save()

        # iterate over all text types and save them
        for field_name, value in form.cleaned_data.items():

            if field_name in form.short_text_fields or field_name in form.long_text_fields:

                taxon_text_type = form.text_type_map[field_name]

                taxon_text, created = TaxonText.objects.get_or_create(taxon_profile=self.taxon_profile,
                                                                      taxon_text_type=taxon_text_type)

                if field_name in form.short_text_fields:
                    taxon_text.text = value

                elif field_name in form.long_text_fields:
                    taxon_text.long_text = value

                taxon_text.save()
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['saved'] = True
        return self.render_to_response(context)
    


class DeleteTaxonProfile(AjaxDeleteView):
    model = TaxonProfile
    template_name = 'taxon_profiles/ajax/delete_taxon_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_type = ContentType.objects.get_for_model(TaxonProfiles)
        url_kwargs = {
            'meta_app_id': self.kwargs['meta_app_id'],
            'content_type_id': content_type.id,
            'object_id': self.object.taxon_profiles.id,
        }
        context['next'] = reverse('manage_taxonprofiles', kwargs=url_kwargs)
        return context


class ChangeTaxonProfilePublicationStatus(MetaAppMixin, FormView):

    form_class = TaxonProfileStatusForm
    template_name = 'taxon_profiles/ajax/change_taxon_profile_publication_status.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon_profile(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_taxon_profile(self, **kwargs):
        self.taxon_profile = TaxonProfile.objects.get(pk=kwargs['taxon_profile_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_profile'] = self.taxon_profile
        context['success'] = False
        return context

    def get_initial(self):
        initial = super().get_initial()
        if self.taxon_profile.publication_status == None:
            initial['publication_status'] = 'publish'
        else:
            initial['publication_status'] = self.taxon_profile.publication_status
            
        initial['is_featured'] = self.taxon_profile.is_featured

        return initial

    def form_valid(self, form):

        self.taxon_profile.publication_status = form.cleaned_data['publication_status']
        self.taxon_profile.is_featured = form.cleaned_data.get('is_featured', False)
        self.taxon_profile.save()

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)



class BatchChangeNatureGuideTaxonProfilesPublicationStatus(MetaAppMixin, FormView):

    form_class = GenericContentStatusForm
    template_name = 'taxon_profiles/ajax/batch_change_taxon_profiles_publication_status.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_nature_guide(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_nature_guide(self, **kwargs):
        self.set_meta_app(**kwargs)
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])
        self.nature_guide = NatureGuide.objects.get(pk=kwargs['nature_guide_id'])
        nature_guide_links = self.meta_app.get_generic_content_links(NatureGuide).exclude(object_id=self.nature_guide.id)
        self.meta_app_nature_guide_ids = nature_guide_links.values_list('object_id', flat=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_profiles'] = self.taxon_profiles
        context['nature_guide'] = self.nature_guide
        context['success'] = False
        return context
    
    def change_taxon_profile_publication_status(self, taxon_profile, publication_status):
        # check if the taxon occurs in another nature guide which is published
        change_status = True

        if publication_status == 'draft':
            occurrences = MetaNode.objects.filter(taxon_source=taxon_profile.taxon_source,
                name_uuid=taxon_profile.name_uuid, nature_guide__in=self.meta_app_nature_guide_ids)
            
            for occurrence in occurrences:
                nature_guide = occurrence.nature_guide
                ng_publication_status = nature_guide.get_option(self.meta_app, 'publication_status')
                if ng_publication_status != 'draft':
                    change_status = False
                    break
                
        if change_status == True:
            taxon_profile.publication_status = publication_status
            taxon_profile.save()
    
    def form_valid(self, form):

        publication_status = form.cleaned_data['publication_status']
        
        results = MetaNode.objects.filter(nature_guide=self.nature_guide,
                node_type='result')
        
        for meta_node in results:
            taxon_profile = None

            if meta_node.taxon:
                taxon_source = meta_node.taxon_source
                name_uuid = meta_node.name_uuid
                taxon_profile = TaxonProfile.objects.filter(taxon_profiles=self.taxon_profiles,
                                                taxon_source=taxon_source, name_uuid=name_uuid).first()
                
                if taxon_profile:
                    self.change_taxon_profile_publication_status(taxon_profile, publication_status)
            
            else:
                fallback_taxa = NatureGuidesTaxonTree.objects.filter(meta_node=meta_node, nature_guide=self.nature_guide)
                for fallback_taxon in fallback_taxa:
                    fallback_taxon_profile = TaxonProfile.objects.filter(taxon_profiles=self.taxon_profiles,
                        taxon_source='app_kit.features.nature_guides', name_uuid=fallback_taxon.name_uuid).first()
                    if fallback_taxon_profile:
                        self.change_taxon_profile_publication_status(fallback_taxon_profile, publication_status)


        context = self.get_context_data(**self.kwargs)
        context['success'] = True
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

        taxon_profile_exists = TaxonProfile.objects.filter(taxon_profiles=self.taxon_profiles,
            taxon_source=self.taxon.taxon_source, name_uuid=self.taxon.name_uuid).exists()

        url = None

        url_kwargs = {
            'meta_app_id':self.meta_app.id,
            'taxon_profiles_id' : self.taxon_profiles.id,
            'taxon_source' : self.taxon.taxon_source,
            'name_uuid' : self.taxon.name_uuid,
        }

        if taxon_profile_exists:
            url = reverse('manage_taxon_profile', kwargs=url_kwargs)

        else:
            url = reverse('create_taxon_profile', kwargs=url_kwargs)
            

        data = {
            'url' : url,
            'exists': taxon_profile_exists,
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



class DeleteTaxonTextType(AjaxDeleteView):

    model = TaxonTextType
    template_name = 'taxon_profiles/ajax/delete_taxon_text_type.html'


class ManageTaxonTextTypesOrder(ManageObjectOrder):
    
    def get_container_id(self):
        
        container_id = 'order-ctype-{0}'.format(self.content_type.id)
        if 'taxon_text_type_category_id' in self.kwargs:
            container_id = '{0}-{1}'.format(container_id, self.kwargs['taxon_text_type_category_id'])
            
        container_id = '{0}-container'.format(container_id)
        return container_id

    def get_queryset(self):
        queryset = super().get_queryset()
        taxon_profiles = TaxonProfiles.objects.get(pk=self.kwargs['taxon_profiles_id'])
        
        queryset = queryset.filter(taxon_profiles=taxon_profiles)
        
        category = None
        if 'taxon_text_type_category_id' in self.kwargs:
            category = TaxonTextTypeCategory.objects.get(pk=self.kwargs['taxon_text_type_category_id'])
        
        queryset = queryset.filter(category=category)
        
        return queryset


class CollectTaxonImages(MetaAppFormLanguageMixin, TemplateView):

    template_name = 'taxon_profiles/ajax/collected_taxon_images.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_taxon(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_taxon(self, **kwargs):
        self.taxon_profile = TaxonProfile.objects.get(pk=kwargs['pk'])
        #taxon_source = kwargs['taxon_source']
        #name_uuid = kwargs['name_uuid']
        #taxon = get_taxon(taxon_source, name_uuid)
        self.taxon = LazyTaxon(instance=self.taxon_profile)


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


class CollectTaxonTraits(MetaAppMixin, TemplateView):

    template_name = 'taxon_profiles/ajax/collected_taxon_traits.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_meta_app(**kwargs)
        self.set_taxon(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_taxon(self, **kwargs):
        
        taxon_profiles_link = self.meta_app.get_generic_content_links(TaxonProfiles).first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        taxon_source = kwargs['taxon_source']
        name_uuid = kwargs['name_uuid']

        taxon_profile = TaxonProfile.objects.get(taxon_profiles=taxon_profiles,
                                                 taxon_source=taxon_source, name_uuid=name_uuid)

        #taxon = get_taxon(taxon_source, name_uuid)

        self.taxon = LazyTaxon(instance=taxon_profile)


    def get_taxon_traits(self):

        spaces = []
        
        # sometimes taxon_athor=None is stored as taxon_author='' for unknown reasons
        # as a tresult, this query fails for taxa without author
        #nodes = NatureGuidesTaxonTree.objects.filter(meta_node__taxon_source=self.taxon.taxon_source,
        #        meta_node__taxon_latname=self.taxon.taxon_latname,
        #        meta_node__taxon_author=self.taxon.taxon_author)

        nodes = NatureGuidesTaxonTree.objects.filter(meta_node__name_uuid=self.taxon.name_uuid)
        
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


class ManageTaxonProfileImage(ManageContentImageWithText):
    template_name = 'taxon_profiles/ajax/manage_taxon_profile_image.html'


class DeleteTaxonProfileImage(DeleteContentImage):
    template_name = 'taxon_profiles/ajax/delete_taxon_profile_image.html'


class ManageTaxonProfilesNavigationEntryCommon:
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_instances(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_instances(self, **kwargs):
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])
        self.taxon_profiles_navigation, created = TaxonProfilesNavigation.objects.get_or_create(taxon_profiles=self.taxon_profiles)
        self.navigation_entry = None
        self.parent_navigation_entry = None
        
        navigation_entry_id = kwargs.get('navigation_entry_id', None)
        parent_navigation_entry_id = kwargs.get('parent_navigation_entry_id', None)
        
        if navigation_entry_id:
            self.navigation_entry = TaxonProfilesNavigationEntry.objects.get(pk=navigation_entry_id)
            
        if parent_navigation_entry_id:
            self.parent_navigation_entry = TaxonProfilesNavigationEntry.objects.get(pk=parent_navigation_entry_id)
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_profiles'] = self.taxon_profiles
        context['navigation_entry'] = self.navigation_entry
        context['parent_navigation_entry'] = self.parent_navigation_entry
        context['success'] = False
        context['taxon_success'] = False
        return context
    
    def set_navigation_entry(self):
        
        if not self.navigation_entry:
            self.navigation_entry = TaxonProfilesNavigationEntry(
                navigation = self.taxon_profiles_navigation,
            )
            
            if self.parent_navigation_entry:
                self.navigation_entry.parent = self.parent_navigation_entry
            
            self.navigation_entry.save()


class ManageTaxonProfilesNavigationEntry(ManageTaxonProfilesNavigationEntryCommon, MetaAppFormLanguageMixin, MetaAppMixin, FormView):
    
    form_class = ManageTaxonProfilesNavigationEntryForm
    template_name = 'taxon_profiles/ajax/manage_navigation_entry.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        if self.navigation_entry:
            initial['name'] = self.navigation_entry.name
            initial['description'] = self.navigation_entry.description
        return initial
    
    def form_valid(self, form):
        
        self.set_navigation_entry()
        
        description = form.cleaned_data.get('description', None)
        name = form.cleaned_data.get('name', None)
        
        self.navigation_entry.description = description
        self.navigation_entry.name = name
        
        if self.parent_navigation_entry:
            self.navigation_entry.parent = self.parent_navigation_entry
            
        self.navigation_entry.save()
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        
        return self.render_to_response(context)


class AddTaxonProfilesNavigationEntryTaxon(ManageTaxonProfilesNavigationEntryCommon, MetaAppMixin, FormView):
    
    template_name = 'taxon_profiles/ajax/navigation_entry_taxa.html'
    form_class = AddTaxonProfilesNavigationEntryTaxonForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parent'] = self.parent_navigation_entry
        kwargs['navigation_entry'] = self.navigation_entry
        kwargs['taxon_search_url'] = reverse('search_taxon')
        
        return kwargs
    
    
    def form_valid(self, form):
        
        self.set_navigation_entry()
        
        taxon = form.cleaned_data['taxon']
        
        taxon_link = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=self.navigation_entry
        )
        
        taxon_link.set_taxon(taxon)
        taxon_link.save()
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['taxon_success'] = True
        
        return self.render_to_response(context)


class DeleteTaxonProfilesNavigationEntry(MetaAppMixin, AjaxDeleteView):
    
    model = TaxonProfilesNavigationEntry

    template_name = 'taxon_profiles/ajax/delete_navigation_entry.html'

    def form_valid(self, form):
        
        navigation_entry_id = self.object.id
        
        navigation = self.object.navigation

        self.object.delete()
        
        navigation.save()

        context = {
            'navigation_entry_id' : navigation_entry_id,
            'taxon_profiles': navigation.taxon_profiles,
            'deleted':True,
        }
        return self.render_to_response(context)

        

class GetTaxonProfilesNavigation(MetaAppMixin, TemplateView):
    
    template_name = 'taxon_profiles/ajax/taxon_profiles_navigation.html'
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_instances(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_instances(self, **kwargs):
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])
        self.taxon_profiles_navigation, created = TaxonProfilesNavigation.objects.get_or_create(taxon_profiles=self.taxon_profiles)
        
    def get_context_data(self, **kwargs):
        
        delta = None
        
        if self.taxon_profiles_navigation.last_prerendered_at:
            delta = self.taxon_profiles_navigation.last_prerendered_at - self.taxon_profiles_navigation.last_modified_at
        
        if not delta or delta.total_seconds() < 0:
            self.taxon_profiles_navigation.prerender()
        
        context = super().get_context_data(**kwargs)
        
        context['taxon_profiles_navigation'] = self.taxon_profiles_navigation
        context['taxon_profiles'] = self.taxon_profiles
        context['navigation_entry_content_type'] = ContentType.objects.get_for_model(TaxonProfilesNavigationEntry)
        context['content_image_ctype'] = ContentType.objects.get_for_model(ContentImage)
    
        return context
    
    
class ManageNavigationImage(ManageContentImage):
    
    template_name = 'taxon_profiles/ajax/manage_navigation_image.html'
    
    def save_image(self, form):
        super().save_image(form)
        
        self.content_instance.navigation.save()
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_profiles'] = self.content_instance.navigation.taxon_profiles
        return context


class DeleteNavigationImage(DeleteContentImage):
    
    template_name = 'taxon_profiles/ajax/delete_navigation_image.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        navigation_entry = self.object.content
        context['taxon_profiles'] = navigation_entry.navigation.taxon_profiles
        
        if self.request.method == 'POST':
            navigation_entry.navigation.save()
        return context
    
    
class DeleteTaxonProfilesNavigationEntryTaxon(MetaAppMixin, AjaxDeleteView):
    
    model = TaxonProfilesNavigationEntryTaxa
    
    template_name = 'taxon_profiles/ajax/delete_navigation_entry_taxon.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['navigation_entry'] = self.object.navigation_entry
        context['taxon_profiles'] = self.object.navigation_entry.navigation.taxon_profiles
        return context
    
    
    def form_valid(self, form):
        
        navigation_entry_taxon_id = self.object.id
        
        navigation = self.object.navigation_entry.navigation

        self.object.delete()
        
        navigation.save()

        context = self.get_context_data(**self.kwargs)
        context['navigation_entry_taxon_id'] = navigation_entry_taxon_id
        context['deleted'] = True
        return self.render_to_response(context)
    
    
class GetTaxonProfilesNavigationEntryTaxonProfiles(MetaAppMixin, TemplateView):
    
    template_name = 'taxon_profiles/ajax/navigation_entry_taxon_profiles.html'
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_instances(**kwargs)
        if 'querystring_key' in request.GET:
            self.template_name = 'taxon_profiles/ajax/navigation_entry_taxon_profiles_list.html'
        return super().dispatch(request, *args, **kwargs)
    
    def set_instances(self, **kwargs):
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])
        self.navigation_entry = TaxonProfilesNavigationEntry.objects.get(pk=kwargs['navigation_entry_id'])
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_profiles'] = self.taxon_profiles
        context['navigation_entry'] = self.navigation_entry
        return context
    
    
class PrerenderTaxonProfilesNavigation(MetaAppMixin, TemplateView):
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])
        return super().dispatch(request, *args, **kwargs)
    
    
    def get(self, request, *args, **kwargs):
        
        navigation = TaxonProfilesNavigation.objects.filter(taxon_profiles=self.taxon_profiles).first()
        
        if navigation:
            navigation.prerender()
        
        data = {
            'success': True,
        }
        return JsonResponse(data)
    

class ChangeNavigationEntryPublicationStatus(MetaAppMixin, FormView):

    form_class = GenericContentStatusForm
    template_name = 'taxon_profiles/ajax/change_navigation_entry_publication_status.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_navigation_entry(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_navigation_entry(self, **kwargs):
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])
        self.navigation_entry = TaxonProfilesNavigationEntry.objects.get(pk=kwargs['navigation_entry_id'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_profiles'] = self.taxon_profiles
        context['navigation_entry'] = self.navigation_entry
        context['success'] = False
        return context
    
    def get_initial(self):
        initial = super().get_initial()
        initial['publication_status'] = self.navigation_entry.publication_status
        return initial
    
    def form_valid(self, form):
        
        publication_status = form.cleaned_data['publication_status']
        
        if publication_status == 'publish':
            self.navigation_entry.publish()
        
        elif publication_status == 'draft':
            self.navigation_entry.unpublish()
            
        self.navigation_entry.navigation.prerender()
            
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        
        return self.render_to_response(context)
    
    
class ManageTaxonTextTypeCategory(MetaAppFormLanguageMixin, FormView):
    
    template_name = 'taxon_profiles/ajax/manage_text_type_category.html'
    form_class = ManageTaxonTextTypeCategoryForm
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_category(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_category(self, **kwargs):
        self.taxon_profiles = TaxonProfiles.objects.get(pk=kwargs['taxon_profiles_id'])
        
        self.taxon_profile = TaxonProfile.objects.get(pk=kwargs['taxon_profile_id'])
        #taxon = get_taxon(taxon_profile.taxon_source, taxon_profile.name_uuid)
        self.taxon = LazyTaxon(instance=self.taxon_profile)
        
        self.category = None
        
        if 'taxon_text_type_category_id' in kwargs:
            self.category = TaxonTextTypeCategory.objects.get(pk=kwargs['taxon_text_type_category_id'])
            
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxon_profiles'] = self.taxon_profiles
        context['taxon_profile'] = self.taxon_profile
        context['category'] = self.category
        context['success'] = False
        context['created'] = False
        return context
    
    def get_initial(self):
        initial = super().get_initial()
        initial['taxon_profiles'] = self.taxon_profiles
        return initial


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()

        return form_class(instance=self.category, **self.get_form_kwargs())
    
    
    def form_valid(self, form):
        
        created = False
        if not self.category:
            created = True
            self.category = TaxonTextTypeCategory(
                taxon_profiles=self.taxon_profiles,
            )
            
        self.category.name = form.cleaned_data['name']
        self.category.save()
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        context['created'] = created
        
        return self.render_to_response(context)


class DeleteTaxonTextTypeCategory(MetaAppMixin, AjaxDeleteView):
    
    model = TaxonTextTypeCategory
    template_name = 'taxon_profiles/ajax/delete_taxon_text_type_category.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        taxon_profiles = self.object.taxon_profiles
        taxon_profile = TaxonProfile.objects.get(pk=self.kwargs['taxon_profile_id'])
        context['taxon_profiles'] = taxon_profiles
        context['taxon_profile'] = taxon_profile

        return context
    

class ManageTaxonTextTypeCategoryOrder(ManageObjectOrder):

    def get_queryset(self):
        queryset = super().get_queryset()
        taxon_profiles = TaxonProfiles.objects.get(pk=self.kwargs['taxon_profiles_id'])
        queryset = queryset.filter(taxon_profiles=taxon_profiles)
        
        return queryset
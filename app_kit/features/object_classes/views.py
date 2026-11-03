from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView, View
from django.urls import reverse

from localcosmos_server.decorators import ajax_required
from localcosmos_server.generic_views import AjaxDeleteView
from localcosmos_server.taxonomy.generic import ModelWithTaxon, ModelWithRequiredTaxon

from app_kit.models import MetaApp
from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin


from .forms import ObjectClassForm, AddObjectClassTaxonForm, AddObjectClassLinkForm
from .models import ObjectClasses, ObjectClass, ObjectClassTaxon

 
class ObjectClassesCommon:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_classes = self.generic_content
        object_class_list = ObjectClass.objects.filter(
            object_classes=object_classes,
        )
        context['object_classes'] = object_classes
        context['generic_content'] = object_classes
        context['object_class_list'] = object_class_list
        return context
    

class ManageObjectClasses(ObjectClassesCommon, ManageGenericContent):

    template_name = 'object_classes/manage_object_classes.html'
    
    
class GetObjectClasses(ObjectClassesCommon, MetaAppMixin, TemplateView):
    
    template_name = 'object_classes/ajax/object_classes_list.html'
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_object_classes(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_object_classes(self, **kwargs):
        self.object_classes = ObjectClasses.objects.get(
            pk=kwargs.get('object_classes_id'),
        )
        self.generic_content = self.object_classes
    
    
class ManageObjectClass(ObjectClassesCommon, MetaAppMixin, FormView):

    template_name = 'object_classes/ajax/manage_object_class.html'
    form_class = ObjectClassForm
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_object_classes(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_object_classes(self, **kwargs):
        self.object_classes = ObjectClasses.objects.get(
            pk=kwargs.get('object_classes_id'),
        )
        self.object_class = None
        if 'object_class_id' in kwargs:
            self.object_class = ObjectClass.objects.get(
                pk=kwargs.get('object_class_id'),
            )
        self.generic_content = self.object_classes
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_class'] = self.object_class
        context['success'] = False
        return context
    
    def get_initial(self):
        initial = super().get_initial()
        if self.object_class:
            initial['name'] = self.object_class.name
            initial['scientific_name'] = self.object_class.scientific_name
            initial['description'] = self.object_class.description
        return initial
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object_classes'] = self.object_classes
        kwargs['language'] = self.meta_app.primary_language
        if self.object_class:
            kwargs['instance'] = self.object_class
        return kwargs
    
    def form_valid(self, form):
        form.save()
        
        context = self.get_context_data()
        context['success'] = True
        context['form'] = form
        return self.render_to_response(context)
    
    
class DeleteObjectClass(AjaxDeleteView):
    model = ObjectClass


class DeleteObjectClassTaxon(AjaxDeleteView):
    model = ObjectClassTaxon
    
    
class AddObjectClassTaxon(MetaAppMixin, FormView):
    template_name = 'object_classes/ajax/add_object_class_taxon.html'
    form_class = AddObjectClassTaxonForm
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_object_class(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_object_class(self, **kwargs):
        self.object_class = ObjectClass.objects.get(
            pk=kwargs.get('object_class_id'),
        )
        self.object_classes = self.object_class.object_classes
        
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object_class'] = self.object_class
        kwargs['taxon_search_url'] = reverse('search_taxon')
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_class'] = self.object_class
        context['object_classes'] = self.object_classes
        context['success'] = False
        return context
    
    def form_valid(self, form):
        
        taxon = form.cleaned_data['taxon']
        
        taxon_link = ObjectClassTaxon(
            object_class=self.object_class,
        )
        
        taxon_link.set_taxon(taxon)
        taxon_link.save()
        
        context = self.get_context_data()
        context['success'] = True
        context['form'] = form
        return self.render_to_response(context)


class SetObjectClassLink(MetaAppMixin, FormView):
    """
    Generic view that assigns an ObjectClass to any model instance whose model
    uses ModelWithTaxon or ModelWithRequiredTaxon.  The target model must have
    an ``object_class`` ForeignKey to ObjectClass.

    URL kwargs expected:
      - object_classes_id  – pk of the ObjectClasses feature instance
      - content_type_id    – pk of the ContentType for the target model
      - object_id          – pk of the target model instance
    """

    template_name = 'object_classes/ajax/set_object_class_link.html'
    form_class = AddObjectClassLinkForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_linked_instance(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_linked_instance(self, **kwargs):
        # get object class by meta_app
        meta_app = MetaApp.objects.get(pk=kwargs['meta_app_id'])
        generic_content_links = meta_app.get_generic_content_links(ObjectClasses)
        self.object_classes = generic_content_links.first().generic_content
        
        content_type = ContentType.objects.get_for_id(kwargs['content_type_id'])
        self.linked_instance = content_type.get_object_for_this_type(
            pk=kwargs['object_id'],
        )
        if not isinstance(self.linked_instance, (ModelWithTaxon, ModelWithRequiredTaxon)):
            raise Http404(
                f"{self.linked_instance.__class__.__name__} must use "
                "ModelWithTaxon or ModelWithRequiredTaxon."
            )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object_classes'] = self.object_classes
        lazy_taxon = self.linked_instance.taxon
        kwargs['taxon'] = lazy_taxon
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['linked_instance'] = self.linked_instance
        context['object_classes'] = self.object_classes
        context['success'] = False
        return context

    def form_valid(self, form):
        self.linked_instance.object_class = form.cleaned_data['object_class']
        self.linked_instance.save()

        context = self.get_context_data()
        context['success'] = True
        context['form'] = form
        return self.render_to_response(context)


class GetObjectClassesForTaxon(MetaAppMixin, View):
    """
    Returns a JSON list of ObjectClass entries for the given taxon.
    Always includes universal classes (no taxa assigned).
    If taxon_source and taxon_nuid are supplied, also includes classes
    whose taxa are ancestors of (or equal to) the given taxon.

    Query parameters: taxon_source, taxon_nuid
    """

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        taxon_source = request.GET.get('taxon_source', '')
        taxon_nuid = request.GET.get('taxon_nuid', '')

        object_classes_link = self.meta_app.get_generic_content_links(ObjectClasses).first()

        if not object_classes_link:
            return JsonResponse([], safe=False)

        object_classes = object_classes_link.generic_content

        universal_pks = ObjectClass.objects.filter(
            object_classes=object_classes,
            taxon_mappings__isnull=True,
        ).values_list('pk', flat=True)

        compatible_pks = []
        if taxon_source and taxon_nuid:
            valid_nuids = [taxon_nuid[:i] for i in range(3, len(taxon_nuid) + 1, 3)]
            compatible_pks = ObjectClassTaxon.objects.filter(
                object_class__object_classes=object_classes,
                taxon_source=taxon_source,
                taxon_nuid__in=valid_nuids,
            ).values_list('object_class_id', flat=True)

        result_qs = ObjectClass.objects.filter(
            Q(pk__in=universal_pks) | Q(pk__in=compatible_pks)
        ).order_by('name')

        data = [{'scientific_name': oc.scientific_name, 'name': oc.name} for oc in result_qs]
        return JsonResponse(data, safe=False)


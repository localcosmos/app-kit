from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView

from localcosmos_server.decorators import ajax_required

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin


from .forms import ObjectClassForm
from .models import ObjectClasses, ObjectClass, ObjectClassTaxon


class ManageObjectClasses(ManageGenericContent):

    template_name = 'object_classes/manage_object_classes.html'
    
    
class GetObjectClasses(MetaAppMixin, TemplateView):
    
    template_name = 'object_classes/ajax/object_classes_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_class_list = ObjectClass.objects.filter(
            object_classes__pk=kwargs.get('object_classes_id'),
        ).order_by('name')
        context['object_class_list'] = object_class_list
        return context
    
    
class ManageObjectClass(MetaAppMixin, FormView):

    template_name = 'object_classes/manage_object_class.html'
    form_class = ObjectClassForm
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_object_classes(**kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def set_object_classes(self, **kwargs):
        self.object_classes = ObjectClasses.objects.get(
            pk=kwargs.get('object_classes_id'),
        )
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_classes'] = self.object_classes
        context['success'] = False
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object_classes'] = self.object_classes
        return kwargs
    
    def form_valid(self, form):
        form.save()
        
        context = self.get_context_data()
        context['success'] = True
        context['form'] = form
        return self.render_to_response(context)
    
from django.utils.translation import gettext as _
from django.contrib.contenttypes.models import ContentType
from django.views.generic import TemplateView, FormView


from .models import (GenericForm, GenericField, GenericValues, DEFAULT_WIDGETS, DJANGO_FIELD_CLASSES, 
    FIELD_OPTIONS, GenericFieldToGenericForm)

from .forms import (GenericFieldForm, AddValueForm, GenericFormOptionsForm)


from django.utils.decorators import method_decorator
from localcosmos_server.decorators import ajax_required


from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin, FormLanguageMixin


class ManageGenericForm(ManageGenericContent):

    template_name = 'generic_forms/manage_generic_form.html'
    options_form_class = GenericFormOptionsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_generic_field_links = GenericFieldToGenericForm.objects.filter(generic_form=self.generic_content).order_by('position')
        
        generic_fields = all_generic_field_links.filter(generic_field__role='regular').order_by('position')
        
        context['taxonomic_reference_field'] = all_generic_field_links.filter(
            generic_field__role='taxonomic_reference').first()
        context['temporal_reference_field'] = all_generic_field_links.filter(
            generic_field__role='temporal_reference').first()
        context['geographic_reference_field'] = all_generic_field_links.filter(
            generic_field__role='geographic_reference').first()
        
        context['generic_fields'] = generic_fields
        context['fieldclasses'] = DJANGO_FIELD_CLASSES # needed for add field button
        #context['search_taxon_form'] = SearchTaxonForm()
        context['generic_field_link_content_type'] = ContentType.objects.get_for_model(
            GenericFieldToGenericForm)
        context['generic_form'] = self.generic_content
        return context


class ManageGenericFormField(MetaAppMixin, FormLanguageMixin, FormView):

    form_class = GenericFieldForm
    template_name = 'generic_forms/ajax/manage_generic_field.html'
    field_template_name = 'generic_forms/generic_field_modify.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_generic_field(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_generic_field(self, **kwargs):
        self.generic_form = GenericForm.objects.get(pk=kwargs['generic_form_id'])

        self.generic_field = None
        self.generic_field_class = None

        self.generic_field_link = None
        
        if 'generic_field_id' in kwargs:
            self.generic_field = GenericField.objects.get(pk=kwargs['generic_field_id'])
            self.generic_field_class = self.generic_field.field_class

            self.generic_field_link = GenericFieldToGenericForm.objects.get(generic_form=self.generic_form,
                                                                            generic_field=self.generic_field)

        if 'generic_field_class' in kwargs:
            self.generic_field_class = kwargs['generic_field_class']
        

    def set_primary_language(self):
        self.primary_language = self.generic_form.primary_language


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['generic_form'] = self.generic_form
        context['generic_field_class'] = self.generic_field_class
        context['generic_field'] = self.generic_field
        context['generic_field_link'] = self.generic_field_link

        # manage choice field choice order
        context['generic_values_content_type'] = ContentType.objects.get_for_model(GenericValues)

        return context


    def get_initial(self):
        initial = super().get_initial()
        
        if self.generic_field:
                            
            initial = {
                'generic_field_id' : self.generic_field.id,
                'generic_field_class' : self.generic_field_class,
                'widget' : self.generic_field.render_as,
                'label' : self.generic_field.label,
                'help_text' : self.generic_field.help_text,
                'is_required' : self.generic_field_link.is_required,
                'is_sticky' : self.generic_field_link.is_sticky,
                'generic_field_role' : self.generic_field.role,
            }

            # fill options into initial
            field_options = self.generic_field.options
            if field_options:
                option_types = FIELD_OPTIONS.get(self.generic_field_class, [])
                
                for option_type in option_types:
                    
                    option_value = field_options.get(option_type, None)
                    if option_value is not None:
                        initial[option_type] = option_value

        else:

            if self.request.method == 'GET':
                initial = {
                    'generic_field_class' : self.generic_field_class,
                    'widget' : DEFAULT_WIDGETS[self.generic_field_class],
                    'generic_field_role': self.kwargs.get('generic_field_role', 'regular'),
                }
        
        return initial

    
    def form_valid(self, form):

        created = False
        increment_field_version = False

        self.generic_field_class = form.cleaned_data['generic_field_class']

        if not self.generic_field:
            
            self.generic_field = GenericField(
                field_class = self.generic_field_class,
                role = form.cleaned_data['generic_field_role'],
            )

            created = True

        self.generic_field.render_as = form.cleaned_data['widget']

        # adjust generic_field params

        ##### LABEL #####
        # check if label is new
        if not created and self.generic_field.label != form.cleaned_data['label']:
            increment_field_version = True


        ##### INCREMENT FIELD VERSION #####
        if increment_field_version:
            self.generic_field.version = self.generic_field.version + 1

        self.generic_field.label = form.cleaned_data['label']

        ##### OPTIONS #####
        # check field options
        available_options = FIELD_OPTIONS.get(self.generic_field_class, [])

        if self.generic_field.options:
            field_options = self.generic_field.options
        else:
            field_options = {}

        # this covers only language independant values, stored in options
        for option_type in available_options:

            option = form.cleaned_data.get(option_type, None)

            if option is not None:
                field_options[option_type] = option

            elif option_type in field_options:
                del field_options[option_type]

        self.generic_field.options = field_options
        self.generic_field.help_text = form.cleaned_data.get('help_text', None)

        # save generic field            
        self.generic_field.save(self.generic_form)

        ##### VALUES #####
        if self.generic_field_class == 'ChoiceField':
            default_value = self.request.POST.get('default_value', None)

            if default_value:
                generic_value = GenericValues.objects.filter(pk=default_value).first()
                if generic_value:
                    generic_value.is_default = True
                    generic_value.save()

            else:
                generic_value = GenericValues.objects.filter(generic_field=self.generic_field,
                                                             is_default=True).first()
                if generic_value:
                    generic_value.is_default=False
                    generic_value.save()

        if not self.generic_field_link:

            position = GenericFieldToGenericForm.objects.filter(generic_form=self.generic_form).count() + 1

            self.generic_field_link = GenericFieldToGenericForm(
                generic_form = self.generic_form,
                generic_field = self.generic_field,
                position = position,
            )

        ##### LINK PARAMETERS #####
        if self.generic_field.role in ['temporal_reference', 'geographic_reference']:
            self.generic_field_link.is_required = True
        else:
            self.generic_field_link.is_required = form.cleaned_data.get('is_required', False)
        self.generic_field_link.is_sticky = form.cleaned_data.get('is_sticky', False)

        # save generic_field_link
        self.generic_field_link.save()

        context = self.get_context_data(**self.kwargs)
        context.update({
            'success' : True,
            'created' : created,
            'form' : form,
        })

        return self.render_to_response(context)


class GetGenericField(MetaAppMixin, TemplateView):

    template_name = 'generic_forms/generic_field_modify.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_generic_field(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_generic_field(self, **kwargs):
        self.generic_form = GenericForm.objects.get(pk=kwargs['generic_form_id'])

        self.generic_field = GenericField.objects.get(pk=kwargs['generic_field_id'])

        self.generic_field_link = GenericFieldToGenericForm.objects.get(generic_form=self.generic_form,
                                                                   generic_field=self.generic_field)
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['generic_field_link'] = self.generic_field_link
        return context


        
'''
    Currently, sharing fields across forms is not implemented
    it is prepared because the link between form and field is in a separate table
'''
class DeleteGenericField(MetaAppMixin, TemplateView):

    template_name = 'generic_forms/ajax/delete_generic_field.html'

    @method_decorator(ajax_required)
    def get(self, request, *args, **kwargs):

        context = self.get_context_data(**kwargs)

        generic_field = GenericField.objects.get(pk=kwargs['generic_field_id'])
        
        context.update({
            'generic_field_id' : generic_field.id,
        })
        return self.render_to_response(context)
    

    @method_decorator(ajax_required)
    def post(self, request, *args, **kwargs):

        context = self.get_context_data(**kwargs)

        generic_field = GenericField.objects.filter(pk=kwargs['generic_field_id']).first()
        generic_field_id = None
        
        if generic_field:                
            generic_field_id = generic_field.id
            generic_field.delete()

        context.update({
            'deleted' : True,
            'generic_field_id' : generic_field_id,
        })

        return self.render_to_response(context)


# this is used only for choices
# re-render the choice part of the edit field
class ManageFieldValueCommon(MetaAppMixin, TemplateView):

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_generic_field(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_generic_field(self, **kwargs):
        self.generic_field_link = GenericFieldToGenericForm.objects.get(
            generic_form_id=kwargs['generic_form_id'], generic_field_id=kwargs['generic_field_id'])
        
        self.generic_field = self.generic_field_link.generic_field
        self.generic_form = self.generic_field_link.generic_form
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['generic_form'] = self.generic_form
        context['generic_field'] = self.generic_field
        context['generic_field_link'] = self.generic_field_link
        context['generic_values_content_type'] = ContentType.objects.get_for_model(GenericValues)
        return context


class AddFieldValue(ManageFieldValueCommon):
    
    template_name = 'generic_forms/ajax/manage_generic_field_choices.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        form = AddValueForm(request.POST)

        errors = []

        if form.is_valid():

            value = str(form.cleaned_data['value'])
            language = form.cleaned_data['input_language']

            is_default = False

            if self.generic_field.field_class == 'ChoiceField' and not GenericValues.objects.filter(generic_field=self.generic_field, value_type='choice').exists():
                is_default=True

            new_generic_value, created = GenericValues.objects.get_or_create(
                generic_field = self.generic_field,
                text_value = value,
                value_type = form.cleaned_data['generic_value_type'],
            )

            new_generic_value.is_default = is_default
            new_generic_value.name = value
            new_generic_value.save()

        else:
            errors = form.errors

        context.update({
            'form' : form,
            'errors' : errors,
        })

        return self.render_to_response(context)


class DeleteFieldValue(ManageFieldValueCommon):

    template_name = 'generic_forms/ajax/manage_generic_field_choices.html'

    # post for browser 'send again ?' warning
    # post data is not used
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        generic_value = GenericValues.objects.filter(pk=kwargs['generic_value_id']).first()
        if generic_value:
            generic_value.delete()

        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        self.template_name = 'generic_forms/ajax/delete_generic_value.html'

        context['generic_value_id'] = kwargs['generic_value_id']
        return self.render_to_response(context)

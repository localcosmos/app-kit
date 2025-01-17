from django.test import TestCase, RequestFactory
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithFormTest, ViewTestMixin)


from app_kit.features.generic_forms.views import (ManageGenericForm, ManageGenericFormField, GetGenericField,
                        DeleteGenericField, ManageFieldValueCommon, AddFieldValue, DeleteFieldValue)

from app_kit.features.generic_forms.models import (GenericForm, GenericFieldToGenericForm, DJANGO_FIELD_CLASSES,
                        DEFAULT_WIDGETS, REFERENCE_FIELD_TYPES, GenericField, FIELD_OPTIONS, GenericValues)

from app_kit.features.generic_forms.forms import GenericFormOptionsForm, GenericFieldForm

from app_kit.models import MetaAppGenericContent


class WithGenericForm:

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(GenericForm)
        
        # create link
        generic_content_name = '{0} {1}'.format(self.meta_app.name, GenericForm.__class__.__name__)
        self.generic_content = GenericForm.objects.create(generic_content_name, self.meta_app.primary_language)

        self.link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=self.content_type,
            object_id=self.generic_content.id
        )

        self.link.save() 


class TestManageGenericForm(ViewTestMixin, WithAdminOnly, WithLoggedInUser, WithUser, WithGenericForm,
                            WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_genericform'
    view_class = ManageGenericForm

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return url_kwargs

    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.generic_content = self.generic_content
        view.generic_content_type = self.content_type
        return view


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['taxonomic_reference_field'], None)
        self.assertEqual(context['geographic_reference_field'], None)
        self.assertEqual(context['temporal_reference_field'], None)
        self.assertEqual(len(context['generic_fields']), 0)
        self.assertIn('fieldclasses', context)
        gfl_ct = ContentType.objects.get_for_model(GenericFieldToGenericForm)
        self.assertEqual(context['generic_field_link_content_type'], gfl_ct)
        self.assertEqual(context['generic_form'], self.generic_content)
        

    @test_settings
    def test_post(self):

        post_data = {
            'is_default' : True,
        }

        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        self.make_user_tenant_admin(self.user, self.tenant)
        response = self.tenant_client.post(self.get_url(), post_data, **url_kwargs)
        self.assertEqual(response.status_code, 200)
        


class WithGenericField:

    def create_all_generic_fields(self):
        # create one generic field per class
        self.generic_field_links = []
        
        for tup in DJANGO_FIELD_CLASSES:
            field_class = tup[0]

            generic_field_link = self.create_generic_field_with_link(field_class)

            self.generic_field_links.append(generic_field_link)


    def create_generic_field_with_link(self, field_class):

        widget = DEFAULT_WIDGETS[field_class]

        generic_field = GenericField(
            field_class = field_class,
            render_as = widget,
            role = 'regular',
            label = self.field_label,
        )
        generic_field.save(self.generic_content)

        generic_field_link = GenericFieldToGenericForm(
            generic_form = self.generic_content,
            generic_field = generic_field,
            position = 1,
        )

        generic_field_link.save()

        return generic_field_link
        

    def get_view(self, url_kwargs):
        
        factory = RequestFactory()
        url = reverse(self.url_name, kwargs=url_kwargs)
        
        view_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }
        request = factory.get(url, **view_kwargs)

        request.user = self.user
        request.session = self.client.session
        request.tenant = self.tenant

        view = self.view_class()        
        view.request = request
        view.kwargs = url_kwargs
        view.meta_app = self.meta_app

        return view

    def get_create_view_for_post(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_form_id' : self.generic_content.id,
        }

        # 'create_generic_field is used instead of manage_generic_field'
        factory = RequestFactory()
        url = reverse('create_generic_field', kwargs=url_kwargs)
        
        view_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }
        request = factory.get(url, **view_kwargs)

        request.user = self.user
        request.session = self.client.session
        request.tenant = self.tenant

        view = self.view_class()        
        view.request = request
        view.kwargs = url_kwargs
        view.meta_app = self.meta_app

        return view

    def get_form_data(self, field_class, field_role):
        
        widget = DEFAULT_WIDGETS[field_class]
        
        data = {
            'generic_field_class' : field_class,
            'generic_field_role' : field_role,
            'label' : self.field_label,
            'is_required' : False,
            'widget' : widget,
            'input_language' : self.generic_content.primary_language,
        }

        option_values = {
            'initial' : '1',
            'min_value' : '0',
            'max_value' : '4',
            'decimal_places' : '2',
            'step' : '1',
            'unit' : 'm',
            'datetime_mode' : 'datetime-local',
        }

        if field_class in FIELD_OPTIONS:
            options = FIELD_OPTIONS[field_class]
            for option in options:
                data[option] = option_values[option]
            
        return data


    def perform_test_initial(self, url_kwargs, field_class, field_role):
        view = self.get_view(url_kwargs)
        view.set_generic_field(**view.kwargs)
        view.set_primary_language()

        initial = view.get_initial()
        self.assertEqual(initial['generic_field_class'], field_class)
        self.assertEqual(initial['widget'], DEFAULT_WIDGETS[field_class])
        self.assertEqual(initial['generic_field_role'], field_role)

        return view, initial


    def perform_test_form_valid(self, field_class, field_role):

        data = self.get_form_data(field_class, field_role)

        self.assertEqual(data['generic_field_class'], field_class)
        
        form = GenericFieldForm(data=data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_create_view_for_post()
        view.set_generic_field(**view.kwargs)
        
        self.assertEqual(view.generic_field_class, None)
        self.assertEqual(view.generic_field, None)
        self.assertEqual(view.generic_field_link, None)
        
        view.set_primary_language()
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)

        field_link = GenericFieldToGenericForm.objects.filter(generic_form=self.generic_content).order_by(
            'pk').last()
        
        if field_link.generic_field.role in ['temporal_reference', 'geographic_reference']:
            self.assertEqual(field_link.is_required, True)
        else:
            self.assertEqual(field_link.is_required, False)
        self.assertEqual(field_link.is_sticky, False)

        generic_field = field_link.generic_field
        expected_widget = DEFAULT_WIDGETS[field_class]
        self.assertEqual(generic_field.field_class, field_class)
        self.assertEqual(generic_field.role, field_role)
        self.assertEqual(generic_field.render_as, expected_widget)
        self.assertEqual(generic_field.label, self.field_label)
        

class TestCreateGenericFormField(WithGenericField, ViewTestMixin, WithLoggedInUser, WithUser, WithGenericForm,
                             WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_generic_field'
    view_class = ManageGenericFormField
    field_label = 'Test label'
    field_role = 'regular'

    @test_settings
    def test_get(self):

        for tup in DJANGO_FIELD_CLASSES:
            field_class = tup[0]
            
            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_class' : field_class,
            }

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            url = reverse(self.url_name, kwargs=url_kwargs)

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.get(url, **view_kwargs)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['meta_app'], self.meta_app)
            

    @test_settings
    def test_set_generic_field(self):

        for tup in DJANGO_FIELD_CLASSES:
            field_class = tup[0]
            
            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_class' : field_class,
            }

            view = self.get_view(url_kwargs)
            view.set_generic_field(**view.kwargs)
            self.assertEqual(view.generic_form, self.generic_content)
            self.assertEqual(view.generic_field, None)
            self.assertEqual(view.generic_field_link, None)
            self.assertEqual(view.generic_field_class, field_class)


    @test_settings
    def test_set_primary_language(self):
        for tup in DJANGO_FIELD_CLASSES:
            field_class = tup[0]
            
            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_class' : field_class,
            }
            view = self.get_view(url_kwargs)
            view.set_generic_field(**view.kwargs)
            view.set_primary_language()
            self.assertEqual(view.primary_language, self.generic_content.primary_language)
         

    @test_settings
    def test_get_context_data(self):
        for tup in DJANGO_FIELD_CLASSES:
            field_class = tup[0]
            
            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_class' : field_class,
            }
            
            view = self.get_view(url_kwargs)
            
            view.set_generic_field(**view.kwargs)
            view.set_primary_language()

            context = view.get_context_data(**view.kwargs)
            self.assertEqual(context['generic_form'], self.generic_content)
            self.assertEqual(context['generic_field_class'], field_class)
            self.assertEqual(context['generic_field'], None)
            self.assertEqual(context['generic_field_link'], None)
            self.assertEqual(context['meta_app'], self.meta_app)
        

    @test_settings
    def test_get_initial(self):
        for tup in DJANGO_FIELD_CLASSES:
            field_class = tup[0]
            
            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_class' : field_class,
            }
            view, initial = self.perform_test_initial(url_kwargs, field_class, self.field_role)
            

    @test_settings
    def test_form_valid(self):
        for tup in DJANGO_FIELD_CLASSES:
            field_class = tup[0]
            
            self.assertEqual(self.generic_content.published_version, None)
            self.assertEqual(self.generic_content.current_version, 1)
            self.perform_test_form_valid(field_class, self.field_role)

            self.generic_content.refresh_from_db()

            self.assertEqual(self.generic_content.published_version, None)
            self.assertEqual(self.generic_content.current_version, 1)

    @test_settings
    def test_form_valid_form_version_bump(self):

        self.generic_content.save(set_published_version=True)
        self.generic_content.refresh_from_db()

        field_class = DJANGO_FIELD_CLASSES[0][0]
        
        self.assertEqual(self.generic_content.published_version, 1)
        self.assertEqual(self.generic_content.current_version, 1)
        self.perform_test_form_valid(field_class, self.field_role)

        self.generic_content.refresh_from_db()

        self.assertEqual(self.generic_content.published_version, 1)
        self.assertEqual(self.generic_content.current_version, 2)
    
        

class TestCreateReferenceField(WithGenericField, ViewTestMixin, WithLoggedInUser, WithUser,  WithGenericForm,
                               WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_generic_field'
    view_class = ManageGenericFormField
    
    field_label = 'Test label'
    field_classes = {
        'taxonomic_reference' : 'TaxonField',
        'geographic_reference' : 'PointJSONField',
        'temporal_reference' : 'DateTimeJSONField'
    }
    

    @test_settings
    def test_get(self):

        for role in REFERENCE_FIELD_TYPES:
            
            field_class = self.field_classes[role]
            
            url_kwargs = self.get_url_kwargs(role, field_class)

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            url = reverse(self.url_name, kwargs=url_kwargs)

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.get(url, **view_kwargs)
            self.assertEqual(response.status_code, 200)

    def get_url_kwargs(self, role, field_class):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_form_id' : self.generic_content.id,
            'generic_field_class' : field_class,
            'generic_field_role' : role,
        }

        return url_kwargs

    @test_settings
    def test_set_generic_field(self):

        for role in REFERENCE_FIELD_TYPES:
            
            field_class = self.field_classes[role]
            
            url_kwargs = self.get_url_kwargs(role, field_class)
            
            view = self.get_view(url_kwargs)
            view.set_generic_field(**view.kwargs)
            self.assertEqual(view.generic_form, self.generic_content)
            self.assertEqual(view.generic_field, None)
            self.assertEqual(view.generic_field_link, None)
            self.assertEqual(view.generic_field_class, field_class)


    @test_settings
    def test_get_initial(self):

        for role in REFERENCE_FIELD_TYPES:
            
            field_class = self.field_classes[role]
            
            url_kwargs = self.get_url_kwargs(role, field_class)
            view, initial = self.perform_test_initial(url_kwargs, field_class, role)
            

    @test_settings
    def test_form_valid(self):
        
        for role in REFERENCE_FIELD_TYPES:
            
            field_class = self.field_classes[role]

            self.perform_test_form_valid(field_class, role)




# manage existing field
class TestManageGenericFormField(WithGenericField, ViewTestMixin, WithLoggedInUser, WithUser, WithGenericForm, 
                                 WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'edit_generic_field'
    view_class = ManageGenericFormField
    field_role = 'regular'
    field_label = 'Test label'


    def setUp(self):
        super().setUp()
        self.create_all_generic_fields()


    @test_settings
    def test_get(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field

            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_id' : generic_field.id,
            }

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            url = reverse(self.url_name, kwargs=url_kwargs)

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.get(url, **view_kwargs)
            self.assertEqual(response.status_code, 200)

            self.assertEqual(response.context_data['meta_app'], self.meta_app)

    
    @test_settings
    def test_set_generic_field(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field

            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_id' : generic_field.id,
            }

            view = self.get_view(url_kwargs)

            view.set_generic_field(**view.kwargs)
            self.assertEqual(view.generic_field, generic_field)
            self.assertEqual(view.generic_field_class, generic_field.field_class)
            self.assertEqual(view.generic_field_link, field_link)
        

    @test_settings
    def test_get_initial(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field

            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_id' : generic_field.id,
            }

            view = self.get_view(url_kwargs)
            view.set_generic_field(**view.kwargs)

            initial = view.get_initial()
        
            self.assertEqual(initial['generic_field_id'], generic_field.id)
            self.assertEqual(initial['generic_field_class'], generic_field.field_class)
            self.assertEqual(initial['widget'], generic_field.render_as)
            self.assertEqual(initial['label'], self.field_label)
            self.assertEqual(initial['help_text'], None)
            self.assertEqual(initial['is_required'], field_link.is_required)
            self.assertEqual(initial['is_sticky'], field_link.is_sticky)
            self.assertEqual(initial['generic_field_role'], self.field_role)


    @test_settings
    def test_form_valid(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field
            generic_form = field_link.generic_form

            self.assertEqual(generic_form.published_version, None)
            self.assertEqual(generic_form.current_version, 1)

            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_id' : generic_field.id,
            }

            view = self.get_view(url_kwargs)
            view.set_generic_field(**view.kwargs)
            view.set_primary_language()

            self.assertEqual(view.generic_field_class, generic_field.field_class)
            self.assertEqual(view.generic_field, generic_field)
            self.assertEqual(view.generic_field_link, field_link)

            data = self.get_form_data(generic_field.field_class, generic_field.role)
            data['label'] = 'Edited label {0}'.format(generic_field.field_class)

            form = GenericFieldForm(data=data)

            is_valid = form.is_valid()
            self.assertEqual(form.errors, {})

            response = view.form_valid(form)
            self.assertEqual(response.status_code, 200)

            field_link = GenericFieldToGenericForm.objects.filter(generic_form=self.generic_content).order_by(
                'pk').last()
            self.assertEqual(field_link.is_required, False)
            self.assertEqual(field_link.is_sticky, False)
            
            generic_field.refresh_from_db()
            self.assertEqual(generic_field.label, data['label'])

            self.assertEqual(generic_form.published_version, None)
            self.assertEqual(generic_form.current_version, 1)

    
    @test_settings
    def test_form_valid_version_bump(self):
        
        field_link = self.generic_field_links[0]

        generic_field = field_link.generic_field
        generic_form = field_link.generic_form

        generic_form.save(set_published_version=True)

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 1)

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_form_id' : self.generic_content.id,
            'generic_field_id' : generic_field.id,
        }

        view = self.get_view(url_kwargs)
        view.set_generic_field(**view.kwargs)
        view.set_primary_language()

        data = self.get_form_data(generic_field.field_class, generic_field.role)
        data['label'] = 'Edited label {0}'.format(generic_field.field_class)

        form = GenericFieldForm(data=data)

        is_valid = form.is_valid()

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)

        generic_form.refresh_from_db()

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 2)



    @test_settings
    def test_form_valid_generic_values_choicefield(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field

            if generic_field.field_class == 'ChoiceField':

                generic_value = GenericValues(
                    generic_field = generic_field,
                    text_value = 'choice 1',
                    value_type = 'choice',
                    is_default = True,
                )

                generic_value.save()

                generic_value_2 = GenericValues(
                    generic_field = generic_field,
                    text_value = 'choice 2',
                    value_type = 'choice',
                    is_default = False,
                )

                generic_value_2.save()

                url_kwargs = {
                    'meta_app_id' : self.meta_app.id,
                    'generic_form_id' : self.generic_content.id,
                    'generic_field_id' : generic_field.id,
                }

                view = self.get_view(url_kwargs)
                view.set_generic_field(**view.kwargs)
                view.set_primary_language()

                

                data = self.get_form_data(generic_field.field_class, generic_field.role)
                view.request.POST = {
                    'default_value': generic_value_2.pk,
                }

                form = GenericFieldForm(data=data)

                is_valid = form.is_valid()
                self.assertEqual(form.errors, {})

                response = view.form_valid(form)
                self.assertEqual(response.status_code, 200)

                generic_value.refresh_from_db()
                generic_value_2.refresh_from_db()

                self.assertFalse(generic_value.is_default)
                self.assertTrue(generic_value_2.is_default)



class TestGetGenericField(WithGenericField, ViewTestMixin, WithLoggedInUser, WithUser,
                          WithGenericForm, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'get_generic_field'
    view_class = GetGenericField

    field_label = 'Test label'

    def setUp(self):
        super().setUp()
        self.create_all_generic_fields()

    def get_view(self, generic_field):

        factory = RequestFactory()
        
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_form_id' : self.generic_content.id,
            'generic_field_id' : generic_field.id,
        }
        
        url = reverse(self.url_name, kwargs=url_kwargs)
        
        view_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }
        request = factory.get(url, **view_kwargs)

        request.user = self.user
        request.session = self.client.session
        request.tenant = self.tenant

        view = self.view_class()        
        view.request = request
        view.kwargs = url_kwargs
        view.meta_app = self.meta_app

        return view
        
        
    @test_settings
    def test_get(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field

            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_id' : generic_field.id,
            }

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            url = reverse(self.url_name, kwargs=url_kwargs)

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.get(url, **view_kwargs)
            self.assertEqual(response.status_code, 200)


    @test_settings
    def test_set_generic_field(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field

            view = self.get_view(generic_field)

            view.set_generic_field(**view.kwargs)
            self.assertEqual(view.generic_form, self.generic_content)
            self.assertEqual(view.generic_field, generic_field)
            self.assertEqual(view.generic_field_link, field_link)


    @test_settings
    def test_get_context_data(self):

        for field_link in self.generic_field_links:
            generic_field = field_link.generic_field

            view = self.get_view(generic_field)
            view.set_generic_field(**view.kwargs)

            context = view.get_context_data(**view.kwargs)
            self.assertEqual(context['meta_app'], self.meta_app)
            self.assertEqual(context['generic_field_link'], field_link)
            


class TestDeleteGenericField(WithGenericField, ViewTestMixin, WithLoggedInUser, WithUser,
                          WithGenericForm, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_generic_field'
    view_class = DeleteGenericField

    field_label = 'Test label'

    def setUp(self):
        super().setUp()
        self.create_all_generic_fields()


    @test_settings
    def test_get(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field

            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_field_id' : generic_field.id,
            }

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            url = reverse(self.url_name, kwargs=url_kwargs)

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.get(url, **view_kwargs)
            self.assertEqual(response.status_code, 200)
            

    @test_settings
    def test_post(self):

        for field_link in self.generic_field_links:

            generic_field = field_link.generic_field
            generic_form = field_link.generic_form

            self.assertEqual(generic_form.published_version, None)
            self.assertEqual(generic_form.current_version, 1)

            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_field_id' : generic_field.id,
            }

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            url = reverse(self.url_name, kwargs=url_kwargs)

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.post(url, **view_kwargs)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['deleted'], True)
            self.assertEqual(response.context_data['generic_field_id'], generic_field.id)

            field_exists = GenericField.objects.filter(pk=generic_field.id)
            self.assertFalse(field_exists.exists())

            link_exists = GenericFieldToGenericForm.objects.filter(generic_field_id=generic_field.id)
            self.assertFalse(link_exists.exists())

            generic_form.refresh_from_db()

            self.assertEqual(generic_form.published_version, None)
            self.assertEqual(generic_form.current_version, 1)


    @test_settings
    def test_post_form_version_bump(self):
        
        field_link = self.generic_field_links[0]

        generic_field = field_link.generic_field
        generic_form = field_link.generic_form

        generic_form.save(set_published_version=True)

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 1)


        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_field_id' : generic_field.id,
        }

        view_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        url = reverse(self.url_name, kwargs=url_kwargs)

        # test with admin role
        self.make_user_tenant_admin(self.user, self.tenant)
        response = self.tenant_client.post(url, **view_kwargs)
        self.assertEqual(response.status_code, 200)

        generic_form.refresh_from_db()
        self.assertEqual(generic_form.current_version, 2)
        self.assertEqual(generic_form.published_version, 1)


class TestManageFieldValueCommon(WithGenericField, ViewTestMixin, WithLoggedInUser, WithUser, WithGenericForm,
                                 WithMetaApp, WithTenantClient, TenantTestCase):

    field_label = 'Test (Multiple) Choice Field'
    view_class = ManageFieldValueCommon

    def setUp(self):
        super().setUp()
        # create a choicefield

        self.generic_field_links = []
        
        for field_class in ['ChoiceField', 'MultipleChoiceField']:

            generic_field_link = self.create_generic_field_with_link(field_class)

            self.generic_field_links.append(generic_field_link)


    def get_url_kwargs(self, generic_field):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_form_id' : self.generic_content.id,
            'generic_field_id' : generic_field.id,
        }
        return url_kwargs


    def get_view(self, generic_field):
        
        url_kwargs = self.get_url_kwargs(generic_field)
        url = reverse('add_generic_field_value', kwargs=url_kwargs)
        
        view_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        factory = RequestFactory()
        request = factory.get(url, **view_kwargs)

        request.user = self.user
        request.session = self.client.session
        request.tenant = self.tenant

        view = self.view_class()        
        view.request = request
        view.kwargs = url_kwargs
        view.meta_app = self.meta_app

        return view
        

    @test_settings
    def test_set_generic_field(self):

        for link in self.generic_field_links:
            generic_field = link.generic_field

            view = self.get_view(generic_field)
            view.set_generic_field(**view.kwargs)

            self.assertEqual(view.generic_field_link, link)
            self.assertEqual(view.generic_field, generic_field)
            self.assertEqual(view.generic_form, self.generic_content)
            

    @test_settings
    def test_set_context_data(self):

        for link in self.generic_field_links:
            generic_field = link.generic_field

            view = self.get_view(generic_field)
            view.set_generic_field(**view.kwargs)

            context = view.get_context_data(**view.kwargs)
            self.assertEqual(context['meta_app'], self.meta_app)
            self.assertEqual(context['generic_form'], self.generic_content)
            self.assertEqual(context['generic_field'], generic_field)
            self.assertEqual(context['generic_field_link'], link)
            self.assertEqual(context['generic_values_content_type'],
                             ContentType.objects.get_for_model(GenericValues))
            


class TestAddFieldValue(WithGenericField, ViewTestMixin, WithLoggedInUser, WithUser, WithGenericForm,
                        WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'add_generic_field_value'
    view_class = AddFieldValue

    field_label = 'Test (Multiple) Choice Field'

    def setUp(self):
        super().setUp()
        # create a choicefield

        self.generic_field_links = []
        
        for field_class in ['ChoiceField', 'MultipleChoiceField']:
            generic_field_link = self.create_generic_field_with_link(field_class)
            self.generic_field_links.append(generic_field_link)
            

    @test_settings
    def test_post(self):

        for link in self.generic_field_links:

            generic_form = link.generic_form
            generic_field = link.generic_field

            post_data = {
                'input_language' : self.generic_content.id,
                'generic_field_id' : generic_field.id,
                'generic_value_type' : 'choice',
                'value' : 'choice value' 
            }

            url_kwargs = {
                'meta_app_id' : self.meta_app.id,
                'generic_form_id' : self.generic_content.id,
                'generic_field_id' : generic_field.id,
            }

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            url = reverse(self.url_name, kwargs=url_kwargs)

            self.assertEqual(generic_form.published_version, None)
            self.assertEqual(generic_form.current_version, 1)

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.post(url, post_data, **view_kwargs)
            self.assertEqual(response.status_code, 200)

            
            created_value = GenericValues.objects.filter(generic_field=generic_field).order_by('pk').last()
            self.assertEqual(created_value.value_type, post_data['generic_value_type'])
            self.assertEqual(created_value.text_value, post_data['value'])

            generic_form.refresh_from_db()

            self.assertEqual(generic_form.published_version, None)
            self.assertEqual(generic_form.current_version, 1)

    @test_settings
    def test_generic_form_version_bump(self):

        link = self.generic_field_links[0]

        generic_form = link.generic_form
        generic_field = link.generic_field
        
        generic_form.save(set_published_version=True)

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 1)


        post_data = {
            'input_language' : self.generic_content.id,
            'generic_field_id' : generic_field.id,
            'generic_value_type' : 'choice',
            'value' : 'choice value' 
        }

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_form_id' : self.generic_content.id,
            'generic_field_id' : generic_field.id,
        }

        view_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        url = reverse(self.url_name, kwargs=url_kwargs)

        self.make_user_tenant_admin(self.user, self.tenant)
        response = self.tenant_client.post(url, post_data, **view_kwargs)
        self.assertEqual(response.status_code, 200)

        generic_form.refresh_from_db()

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 2)

            

class TestDeleteFieldValue(WithGenericField, ViewTestMixin, WithLoggedInUser, WithUser, WithGenericForm,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_generic_field_value'
    view_class = DeleteFieldValue

    field_label = 'Test (Multiple) Choice Field'

    def setUp(self):
        super().setUp()
        # create a choicefield

        self.generic_field_links = []
        
        for field_class in ['ChoiceField', 'MultipleChoiceField']:
            generic_field_link = self.create_generic_field_with_link(field_class)
            self.generic_field_links.append(generic_field_link)


    def get_url(self, generic_field, generic_value):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'generic_form_id' : self.generic_content.id,
            'generic_field_id' : generic_field.id,
            'generic_value_id' : generic_value.id,
        }

        url = reverse(self.url_name, kwargs=url_kwargs)

        return url


    def create_generic_value(self, generic_field):
        # create a value
        generic_value = GenericValues(
            generic_field = generic_field,
            text_value = 'value for {0}'.format(generic_field.field_class),
            value_type = 'choice',
            name = 'value name'
        )

        generic_value.save()

        return generic_value

    
        
    @test_settings
    def test_get(self):

        for link in self.generic_field_links:
            generic_field = link.generic_field

            generic_value = self.create_generic_value(generic_field)

            url = self.get_url(generic_field, generic_value)

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.get(url, **view_kwargs)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['generic_value_id'], generic_value.id)
            

    @test_settings
    def test_post(self):

        for link in self.generic_field_links:

            generic_form = link.generic_form
            generic_field = link.generic_field

            self.assertEqual(generic_form.published_version, None)
            self.assertEqual(generic_form.current_version, 1)

            # create a value
            generic_value = self.create_generic_value(generic_field)

            url = self.get_url(generic_field, generic_value)

            view_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)

            generic_value_exists = GenericValues.objects.filter(pk=generic_value.pk)
            self.assertTrue(generic_value_exists.exists())
            
            response = self.tenant_client.post(url, **view_kwargs)
            self.assertEqual(response.status_code, 200)

            self.assertFalse(generic_value_exists.exists())

            generic_form.refresh_from_db()

            self.assertEqual(generic_form.published_version, None)
            self.assertEqual(generic_form.current_version, 1)

    
    @test_settings
    def test_post_form_version_bump(self):

        link = self.generic_field_links[0]

        generic_form = link.generic_form
        generic_field = link.generic_field

        generic_form.save(set_published_version=True)

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 1)


        # create a value
        generic_value = self.create_generic_value(generic_field)

        url = self.get_url(generic_field, generic_value)

        view_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        # test with admin role
        self.make_user_tenant_admin(self.user, self.tenant)        
        response = self.tenant_client.post(url, **view_kwargs)
        self.assertEqual(response.status_code, 200)

        generic_form.refresh_from_db()

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 2)
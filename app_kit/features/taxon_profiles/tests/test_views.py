from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.urls import reverse

from app_kit.tests.common import test_settings

from app_kit.models import MetaAppGenericContent, ContentImage

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, ViewTestMixin, WithImageStore, WithMedia, WithFormTest)

from app_kit.tests.test_views import ContentImagePostData

from app_kit.features.taxon_profiles.views import (ManageTaxonProfiles, ManageTaxonProfile, ManageTaxonTextType,
                DeleteTaxonTextType, CollectTaxonImages, CollectTaxonTraits, ManageTaxonProfileImage,
                DeleteTaxonProfileImage, GetManageOrCreateTaxonProfileURL, ManageTaxonTextTypesOrder,
                ChangeTaxonProfilePublicationStatus, BatchChangeNatureGuideTaxonProfilesPublicationStatus,
                CreateTaxonProfile, ManageTaxonProfilesNavigationEntry, AddTaxonProfilesNavigationEntryTaxon,
                DeleteTaxonProfilesNavigationEntry, GetTaxonProfilesNavigation, ManageNavigationImage,
                DeleteNavigationImage, DeleteTaxonProfilesNavigationEntryTaxon, DeleteTaxonTextTypeCategory,
                ChangeNavigationEntryPublicationStatus, ManageTaxonTextTypeCategory)

from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonProfile, TaxonTextType,
                TaxonText, TaxonProfilesNavigation, TaxonProfilesNavigationEntry,
                TaxonProfilesNavigationEntryTaxa, TaxonTextTypeCategory)

from app_kit.features.taxon_profiles.forms import ManageTaxonTextsForm, ManageTaxonTextTypeForm


from app_kit.features.nature_guides.models import NatureGuide, NatureGuidesTaxonTree, MetaNode
from app_kit.features.nature_guides.tests.common import WithMatrixFilters


from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon



class WithTaxonProfiles:

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(TaxonProfiles)

        self.generic_content_link = MetaAppGenericContent.objects.get(meta_app=self.meta_app,
                                                                      content_type=self.content_type)

        self.generic_content = self.generic_content_link.generic_content


    def create_text_type(self, text_type_name):

        text_type = TaxonTextType(
            taxon_profiles = self.generic_content,
            text_type=text_type_name,
        )

        text_type.save()

        return text_type


class WithTaxonProfile:

    def setUp(self):
        super().setUp()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        self.taxon_profile = TaxonProfile(
            taxon_profiles=self.generic_content,
            taxon=lazy_taxon,
        )

        self.taxon_profile.save()


class WithNatureGuideNode:

    # create a nature guide with taxon to populate context['taxa']
    def setUp(self):
        super().setUp()
        self.nature_guide = NatureGuide.objects.create('Test Nature Guide', 'en')
        link = MetaAppGenericContent(
            meta_app = self.meta_app,
            content_type = ContentType.objects.get_for_model(NatureGuide),
            object_id = self.nature_guide.id,
        )
        link.save()

        self.start_node = NatureGuidesTaxonTree.objects.get(nature_guide=self.nature_guide,
                                                            meta_node__node_type='root')

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        # add a child with taxon
        self.meta_node = MetaNode(
            name='Test meta node',
            nature_guide=self.nature_guide,
            node_type='result',
            taxon=self.lazy_taxon,
        )

        self.meta_node.save()

        self.node = NatureGuidesTaxonTree(
            nature_guide=self.nature_guide,
            meta_node=self.meta_node,
        )

        self.node.save(self.start_node)

        taxa = self.nature_guide.taxa()
        self.assertEqual(taxa.count(), 1)


class TestManageTaxonProfiles(WithNatureGuideNode, WithTaxonProfiles, ViewTestMixin, WithAdminOnly, WithUser,
                              WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_taxonprofiles'
    view_class = ManageTaxonProfiles


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return url_kwargs


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.meta_app = self.meta_app
        view.generic_content = self.generic_content
        view.generic_content_type = self.content_type

        context = view.get_context_data(**view.kwargs)
        self.assertIn('taxa', context)
        self.assertEqual(context['taxa'][0], self.lazy_taxon)
        self.assertEqual(context['searchbackboneform'].__class__, AddSingleTaxonForm)


class TestCreateTaxonProfile(WithNatureGuideNode, WithTaxonProfiles, ViewTestMixin, WithUser, WithLoggedInUser,
                             WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'create_taxon_profile'
    view_class = CreateTaxonProfile

    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)
    

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'taxon_source' : self.lazy_taxon.taxon_source,
            'name_uuid' : self.lazy_taxon.name_uuid
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app

        return view

    @test_settings
    def test_dispatch(self):

        url = self.get_url()
        
        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        response = self.tenant_client.get(url, **url_kwargs)
        self.assertEqual(response.status_code, 403)

        # test with admin role
        self.make_user_tenant_admin(self.user, self.tenant)
        response = self.tenant_client.get(url, **url_kwargs)

        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_set_taxon(self):

        view = self.get_view()
        view.set_taxon(**view.kwargs)
        self.assertEqual(view.taxon_profiles, self.generic_content)
        self.assertEqual(view.taxon, self.lazy_taxon)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_taxon(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['taxon'], self.lazy_taxon)
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        self.assertEqual(context['success'], False)
        

    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.set_taxon(**view.kwargs)

        taxon_profile_qry = TaxonProfile.objects.filter(taxon_profiles=self.generic_content,
                                                    taxon_source=self.lazy_taxon.taxon_source,
                                                    name_uuid=self.lazy_taxon.name_uuid)

        self.assertFalse(taxon_profile_qry.exists())
        response = view.post(view.request, **view.kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)

        self.assertTrue(taxon_profile_qry.exists())


class TestGetManageOrCreateTaxonProfileURL(WithNatureGuideNode, WithTaxonProfiles, ViewTestMixin, WithUser,
                                           WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'get_taxon_profiles_manage_or_create_url'
    view_class = GetManageOrCreateTaxonProfileURL


    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app

        return view

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
        }
        return url_kwargs


    def get_request(self, ajax=False):

        request = super().get_request(ajax=ajax)
        request.GET = {
            'taxon_source' : self.lazy_taxon.taxon_source,
            'name_uuid' : str(self.lazy_taxon.name_uuid),
        }
        return request


    def test_set_taxon(self):
        view = self.get_view()
        view.set_taxon(view.request, **view.kwargs)
        self.assertEqual(view.taxon_profiles, self.generic_content)
        self.assertEqual(view.taxon, self.lazy_taxon)


    def test_get(self):

        view = self.get_view()
        view.set_taxon(view.request, **view.kwargs)
        response = view.get(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)



class TestManageTaxonProfile(WithNatureGuideNode, WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                    WithAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_taxon_profile'
    view_class = ManageTaxonProfile


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app

        return view


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'taxon_source' : 'taxonomy.sources.col',
            'name_uuid' : str(self.taxon_profile.name_uuid),
        }
        return url_kwargs


    @test_settings
    def test_set_taxon(self):

        view = self.get_view()
        view.set_taxon(view.request, **view.kwargs)

        self.assertEqual(view.taxon, self.lazy_taxon)
        self.assertEqual(view.taxon_profile, self.taxon_profile)

        # test with nature guide taxon, not col taxon
        ng_taxon = self.start_node

        lazy_ng_taxon = LazyTaxon(instance=ng_taxon)

        ng_taxon_profile = TaxonProfile(
            taxon_profiles = self.generic_content,
            taxon=lazy_ng_taxon,
        )

        ng_taxon_profile.save()

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'taxon_source' : 'app_kit.features.nature_guides',
            'name_uuid' : str(ng_taxon.name_uuid),
        }

        view = self.get_view()
        view.set_taxon(view.request, **url_kwargs)

        self.assertEqual(view.taxon, lazy_ng_taxon)
    

    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.set_taxon(view.request, **view.kwargs)

        text_type = self.create_text_type('Test text type')

        text_content = 'Test text content'
        long_text_content = 'Test long text'
        long_text_key = '{0}:longtext'.format(text_type.text_type)

        post_data = {
            'input_language' : self.generic_content.primary_language,
        }
        post_data[text_type.text_type] = text_content
        post_data[long_text_key] = long_text_content

        form = ManageTaxonTextsForm(self.generic_content, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context_data['saved'], True)

        taxon_text = TaxonText.objects.get(taxon_text_type=text_type)
        self.assertEqual(taxon_text.text, text_content)
        
        if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
            self.assertEqual(taxon_text.long_text, long_text_content)

        # test update
        text_content_2 = 'Update text content'
        long_text_content_2 = 'Updated long text content'
        post_data[text_type.text_type] = text_content_2
        post_data[long_text_key] = long_text_content_2

        form_2 = ManageTaxonTextsForm(self.generic_content, data=post_data)
        form_2.is_valid()
        self.assertEqual(form_2.errors, {})

        view_2 = self.get_view()
        view_2.set_taxon(view_2.request, **view_2.kwargs)
        response = view_2.form_valid(form_2)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context_data['saved'], True)

        taxon_text = TaxonText.objects.get(taxon_text_type=text_type)
        self.assertEqual(taxon_text.text, text_content_2)
        
        if settings.APP_KIT_ENABLE_TAXON_PROFILES_LONG_TEXTS == True:
            self.assertEqual(taxon_text.long_text, long_text_content_2)


class TestCreateTaxonTextType(WithNatureGuideNode, WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'create_taxon_text_type'
    view_class = ManageTaxonTextType


    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'taxon_source' : self.lazy_taxon.taxon_source,
            'name_uuid' : str(self.lazy_taxon.name_uuid),
        }
        return url_kwargs


    @test_settings
    def test_set_taxon_text_type(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)
        self.assertEqual(view.taxon, self.lazy_taxon)
        self.assertEqual(view.taxon_profiles, self.generic_content)
        self.assertEqual(view.taxon_text_type, None)


    @test_settings
    def test_get_initial(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)

        initial = view.get_initial()
        self.assertEqual(initial['taxon_profiles'], self.generic_content)

    @test_settings
    def test_get_form(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)

        form = view.get_form()
        self.assertEqual(form.__class__, ManageTaxonTextTypeForm)

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['taxon_text_type'], None)
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        self.assertEqual(context['taxon'], self.lazy_taxon)
        

    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)

        text_type_name = 'Test text type'

        post_data = {
            'input_language' : self.generic_content.primary_language,
            'text_type' : text_type_name,
            'taxon_profiles' : self.generic_content.id,
        }

        form = ManageTaxonTextTypeForm(instance=None, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        query = TaxonTextType.objects.filter(text_type=text_type_name)
        self.assertFalse(query.exists())

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['created'], True)
        self.assertEqual(response.context_data['form'].__class__, ManageTaxonTextTypeForm)
        self.assertTrue(query.exists())



class TestManageTaxonTextType(WithNatureGuideNode, WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_taxon_text_type'
    view_class = ManageTaxonTextType


    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        text_type_name = 'Test text type'

        self.taxon_text_type = self.create_text_type(text_type_name)


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_text_type_id' : self.taxon_text_type.id,
            'taxon_profiles_id' : self.generic_content.id,
            'taxon_source' : self.lazy_taxon.taxon_source,
            'name_uuid' : str(self.lazy_taxon.name_uuid),
        }
        return url_kwargs


    @test_settings
    def test_set_taxon_text_type(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)
        self.assertEqual(view.taxon, self.lazy_taxon)
        self.assertEqual(view.taxon_profiles, self.generic_content)
        self.assertEqual(view.taxon_text_type, self.taxon_text_type)

    @test_settings
    def test_get_form(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)

        form = view.get_form()
        self.assertEqual(form.__class__, ManageTaxonTextTypeForm)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['taxon_text_type'], self.taxon_text_type)


    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.set_taxon_text_type(**view.kwargs)

        new_name = 'Updated text type name'

        post_data = {
            'id' : self.taxon_text_type.id,
            'input_language' : self.generic_content.primary_language,
            'text_type' : new_name,
            'taxon_profiles' : self.generic_content.id,
        }


        form = ManageTaxonTextTypeForm(instance=self.taxon_text_type, data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['created'], False)
        self.assertEqual(response.context_data['form'].__class__, ManageTaxonTextTypeForm)

        self.taxon_text_type.refresh_from_db()
        self.assertEqual(self.taxon_text_type.text_type, new_name)




class TestManageTaxonTextTypesOrder(WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_taxon_text_types_order'
    view_class = ManageTaxonTextTypesOrder


    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        text_type_name = 'Test text type'
        second_text_type_name = 'Second text type'

        self.taxon_text_type = self.create_text_type(text_type_name)
        self.second_taxon_text_type = self.create_text_type(second_text_type_name)


    def get_url_kwargs(self):
        content_type = ContentType.objects.get_for_model(TaxonTextType)
        url_kwargs = {
            'content_type_id': content_type.id,
            'taxon_profiles_id' : self.generic_content.id,
        }
        return url_kwargs



class TestDeleteTaxonTextType(WithNatureGuideNode, WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_taxon_text_type'
    view_class = DeleteTaxonTextType


    def setUp(self):
        super().setUp()
        text_type_name = 'Test text type'

        self.taxon_text_type = self.create_text_type(text_type_name)


    def get_url_kwargs(self):
        url_kwargs = {
            'pk' : self.taxon_text_type.id,
        }
        return url_kwargs


class TestCollectTaxonImages(WithNatureGuideNode, WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithImageStore, WithMedia, WithAjaxAdminOnly,
                WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'collect_taxon_images'
    view_class = CollectTaxonImages


    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)


    def create_content_images(self):

        # taxon image
        self.taxon_image_store = self.create_image_store_with_taxon(lazy_taxon=self.lazy_taxon)

        # add image to nature guide meta node
        self.meta_node_image = self.create_content_image(self.meta_node, self.user)

        # add image to nature guide node
        self.node_image = self.create_content_image(self.node, self.user)

        # add image to taxon profile
        self.taxon_profile_image = self.create_content_image(self.taxon_profile, self.user)
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'pk' : self.generic_content.id,
            'taxon_source' : self.lazy_taxon.taxon_source,
            'name_uuid' : str(self.lazy_taxon.name_uuid),
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view


    @test_settings
    def test_dispatch(self):

        self.create_content_images()

        url = self.get_url()
        
        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }

        response = self.tenant_client.get(url, **url_kwargs)
        self.assertEqual(response.status_code, 403)

        # test with admin role
        self.make_user_tenant_admin(self.user, self.tenant)
        response = self.tenant_client.get(url, **url_kwargs)
        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_set_taxon(self):
        
        self.create_content_images()
        
        view = self.get_view()
        view.set_taxon(**view.kwargs)

        self.assertEqual(view.taxon_profile, self.taxon_profile)
        self.assertEqual(view.taxon, self.lazy_taxon)
        

    @test_settings
    def test_get_taxon_profile_images(self):

        self.create_content_images()

        view = self.get_view()
        view.set_taxon(**view.kwargs)

        taxon_profile_images = view.get_taxon_profile_images()
        self.assertEqual(len(taxon_profile_images), 1)
        self.assertEqual(taxon_profile_images[0], self.taxon_profile_image)


    @test_settings
    def test_get_taxon_images(self):

        self.create_content_images()

        view = self.get_view()
        view.set_taxon(**view.kwargs)

        taxon_images = list(view.get_taxon_images())
        self.assertEqual(len(taxon_images), 3)

        self.assertIn(self.taxon_profile_image, taxon_images)
        self.assertIn(self.meta_node_image, taxon_images)
        self.assertIn(self.node_image, taxon_images)
        

    @test_settings
    def test_get_nature_guide_images(self):

        self.create_content_images()

        view = self.get_view()
        view.set_taxon(**view.kwargs)

        nature_guide_images = view.get_nature_guide_images()
        self.assertEqual(len(nature_guide_images), 2)
        self.assertEqual(nature_guide_images[0], self.meta_node_image)
        self.assertEqual(nature_guide_images[1], self.node_image)
        

    @test_settings
    def test_get_context_data(self):

        self.create_content_images()

        view = self.get_view()
        view.set_taxon(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['taxon'], self.lazy_taxon)

        self.assertEqual(len(context['taxon_profile_images']), 1)
        self.assertEqual(len(context['node_images']), 2)
        self.assertEqual(len(context['taxon_images']), 0)



class TestCollectTaxonTraits(WithNatureGuideNode, WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithAjaxAdminOnly, WithMatrixFilters,
                WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'collect_taxon_traits'
    view_class = CollectTaxonTraits


    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        self.parent_node = self.start_node
        self.create_all_matrix_filters(self.parent_node)

        self.fill_matrix_filters_nodes(self.parent_node, [self.node])


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'taxon_source' : self.lazy_taxon.taxon_source,
            'name_uuid' : str(self.lazy_taxon.name_uuid),
        }
        return url_kwargs


    @test_settings
    def test_set_taxon(self):

        view = self.get_view()
        view.set_meta_app(**view.kwargs)
        view.set_taxon(**view.kwargs)

        self.assertEqual(view.taxon, self.lazy_taxon)


    @test_settings
    def test_get_taxon_traits(self):

        view = self.get_view()
        view.set_meta_app(**view.kwargs)
        view.set_taxon(**view.kwargs)
        
        traits = view.get_taxon_traits()

        self.assertEqual(len(traits), 5)

        trait_types = []
        for trait in traits:
            trait_types.append(trait.matrix_filter.filter_type)
            
        expected_types = set(['ColorFilter', 'DescriptiveTextAndImagesFilter', 'NumberFilter', 'RangeFilter',
                              'TextOnlyFilter'])
        self.assertEqual(set(trait_types), expected_types)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_meta_app(**view.kwargs)
        view.set_taxon(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertIn('taxon_traits', context)



class TestManageTaxonProfileImage(WithNatureGuideNode, WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithImageStore, WithMedia, WithAjaxAdminOnly,
                WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'manage_taxon_profile_image'
    view_class = ManageTaxonProfileImage

    def get_url_kwargs(self):

        taxon_profile_ctype = ContentType.objects.get_for_model(TaxonProfile)
        
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : taxon_profile_ctype.id,
            'object_id' : self.taxon_profile.id,
        }
        return url_kwargs



class TestManageTaxonProfileImageWithType(TestManageTaxonProfileImage):

    def get_url_kwargs(self):

        taxon_profile_ctype = ContentType.objects.get_for_model(TaxonProfile)
        
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : taxon_profile_ctype.id,
            'object_id' : self.taxon_profile.id,
            'image_type' : 'test type',
        }
        return url_kwargs
    


class TestManageExistingTaxonProfileImage(TestManageTaxonProfileImage):


    def setUp(self):
        super().setUp()

        self.content_image = self.create_content_image(self.taxon_profile, self.user)
        

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_image_id' : self.content_image.id,
        }
        return url_kwargs


class TestDeleteTaxonProfileImage(TestManageTaxonProfileImage):

    url_name = 'delete_taxon_profile_image'
    view_class = DeleteTaxonProfileImage

    def setUp(self):
        super().setUp()

        self.content_image = self.create_content_image(self.taxon_profile, self.user)
        

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'pk' : self.content_image.id,
        }
        return url_kwargs


class TestChangeTaxonProfilePublicationStatus(WithNatureGuideNode, WithTaxonProfile, WithTaxonProfiles,
                ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
                TenantTestCase):
    
    url_name = 'change_taxon_profile_publication_status'
    view_class = ChangeTaxonProfilePublicationStatus

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profile_id' : self.taxon_profile.id,
        }
        return url_kwargs
    
    @test_settings
    def test_set_taxon_profile(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_taxon_profile(**view.kwargs)
        self.assertEqual(view.taxon_profile, self.taxon_profile)

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_taxon_profile(**view.kwargs)
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['taxon_profile'], self.taxon_profile)
        self.assertFalse(context_data['success'])

    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_taxon_profile(**view.kwargs)

        initial = view.get_initial()
        self.assertEqual(self.taxon_profile.publication_status, None)
        self.assertEqual(initial['publication_status'], 'publish')

        self.taxon_profile.publication_status = 'draft'
        self.taxon_profile.save()
        view.set_taxon_profile(**view.kwargs)

        initial = view.get_initial()
        self.assertEqual(initial['publication_status'], 'draft')

        self.taxon_profile.publication_status = 'publish'
        self.taxon_profile.save()
        view.set_taxon_profile(**view.kwargs)

        initial = view.get_initial()
        self.assertEqual(initial['publication_status'], 'publish')


    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_taxon_profile(**view.kwargs)

        post_data = {
            'publication_status' : 'draft',
        }

        form = view.form_class(data=post_data)
        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})

        self.assertEqual(self.taxon_profile.publication_status, None)

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])

        self.taxon_profile.refresh_from_db()
        self.assertEqual(self.taxon_profile.publication_status, 'draft')


class TestBatchChangeNatureGuideTaxonProfilesPublicationStatus(WithNatureGuideNode, WithTaxonProfile,
        WithTaxonProfiles, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp,
        WithTenantClient, TenantTestCase):
    
    
    url_name = 'batch_change_taxon_profile_publication_status'
    view_class = BatchChangeNatureGuideTaxonProfilesPublicationStatus
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'nature_guide_id': self.nature_guide.id,
        }
        return url_kwargs
    

    def create_second_nature_guide(self):
        self.second_nature_guide = NatureGuide.objects.create('Test Nature Guide 2', 'en')
        link = MetaAppGenericContent(
            meta_app = self.meta_app,
            content_type = ContentType.objects.get_for_model(NatureGuide),
            object_id = self.second_nature_guide.id,
        )
        link.save()

        self.second_start_node = NatureGuidesTaxonTree.objects.get(nature_guide=self.second_nature_guide,
                                                            meta_node__node_type='root')
        
    def add_taxon_to_nature_guide(self, lazy_taxon, nature_guide):

        # add a child with taxon
        self.second_meta_node = MetaNode(
            name='Test meta node',
            nature_guide=nature_guide,
            node_type='result',
            taxon=lazy_taxon,
        )

        self.second_meta_node.save()

        self.second_node = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=self.second_meta_node,
        )

        self.second_node.save(nature_guide.root_node)
    
    @test_settings
    def test_set_nature_guide(self):
        view = self.get_view()
        view.set_nature_guide(**view.kwargs)
        self.assertEqual(view.taxon_profiles, self.generic_content)
        self.assertEqual(view.nature_guide, self.nature_guide)
        self.assertEqual(list(view.meta_app_nature_guide_ids), [])

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.set_nature_guide(**view.kwargs)
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['taxon_profiles'], self.generic_content)
        self.assertEqual(context_data['nature_guide'], self.nature_guide)
        self.assertFalse(context_data['success'])

    @test_settings
    def test_change_taxon_profile_publication_status(self):
        view = self.get_view()
        view.set_nature_guide(**view.kwargs)

        self.assertEqual(self.taxon_profile.publication_status, None)

        view.change_taxon_profile_publication_status(self.taxon_profile, 'draft')
        self.taxon_profile.refresh_from_db()
        self.assertEqual(self.taxon_profile.publication_status, 'draft')

        view.change_taxon_profile_publication_status(self.taxon_profile, 'publish')
        self.taxon_profile.refresh_from_db()
        self.assertEqual(self.taxon_profile.publication_status, 'publish')

        self.create_second_nature_guide()
        self.add_taxon_to_nature_guide(self.lazy_taxon, self.second_nature_guide)

        # does not change to draft beecause taxon is active in second published nature guide
        view.change_taxon_profile_publication_status(self.taxon_profile, 'draft')
        self.taxon_profile.refresh_from_db()
        self.assertEqual(self.taxon_profile.publication_status, 'publish')


    @test_settings
    def test_form_valid(self):
        view = self.get_view()
        view.set_nature_guide(**view.kwargs)
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        picea_abies = models.TaxonTreeModel.objects.get(taxon_latname='Picea abies')
        lazy_taxon_2 = LazyTaxon(instance=picea_abies)
        self.add_taxon_to_nature_guide(lazy_taxon_2, self.nature_guide)

        self.second_taxon_profile = TaxonProfile(
            taxon_profiles=self.generic_content,
            taxon=lazy_taxon_2,
        )

        self.second_taxon_profile.save()

        post_data = {
            'publication_status' : 'draft',
        }

        form = view.form_class(data=post_data)
        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})

        self.assertEqual(self.taxon_profile.publication_status, None)
        self.assertEqual(self.second_taxon_profile.publication_status, None)

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])

        self.taxon_profile.refresh_from_db()
        self.second_taxon_profile.refresh_from_db()
        self.assertEqual(self.taxon_profile.publication_status, 'draft')
        self.assertEqual(self.second_taxon_profile.publication_status, 'draft')


    @test_settings
    def test_form_valid_fallback_taxa(self):
        
        view = self.get_view()
        view.set_nature_guide(**view.kwargs)

        self.add_taxon_to_nature_guide(None, self.nature_guide)

        lazy_taxon_2 = LazyTaxon(instance=self.second_node)

        non_taxon_profile = TaxonProfile(
            taxon_profiles=self.generic_content,
            taxon=lazy_taxon_2,
        )

        non_taxon_profile.save()

        post_data = {
            'publication_status' : 'draft',
        }

        form = view.form_class(data=post_data)
        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})

        self.assertEqual(self.taxon_profile.publication_status, None)
        self.assertEqual(non_taxon_profile.publication_status, None)

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])

        self.taxon_profile.refresh_from_db()
        non_taxon_profile.refresh_from_db()
        self.assertEqual(self.taxon_profile.publication_status, 'draft')
        self.assertEqual(non_taxon_profile.publication_status, 'draft')



class TestCreateTaxonProfilesNavigationEntry(WithTaxonProfiles, ViewTestMixin, WithAjaxAdminOnly, 
        WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):
    
    url_name = 'create_taxonprofiles_navigation_entry'
    view_class = ManageTaxonProfilesNavigationEntry
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
        }
        return url_kwargs
    
    
    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.set_instances(**view.kwargs)
        
        self.assertEqual(view.taxon_profiles, self.generic_content)
        
        nav_query = TaxonProfilesNavigation.objects.filter(taxon_profiles=self.generic_content)
        
        self.assertTrue(nav_query.exists())
        
        self.assertEqual(view.navigation_entry, None)
        self.assertEqual(view.parent_navigation_entry, None)
        
        
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        self.assertEqual(context['navigation_entry'], None)
        self.assertEqual(context['parent_navigation_entry'], None)
        self.assertEqual(context['success'], False)
        self.assertEqual(context['taxon_success'], False)
    
    
    @test_settings
    def test_set_navigation_entry(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        self.assertEqual(view.navigation_entry, None)
        view.set_navigation_entry()
        
        self.assertTrue(view.navigation_entry != None)
    
    
    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        empty_initial = view.get_initial()
        
        self.assertEqual(empty_initial, {})
        
        view.set_navigation_entry()
        
        entry = view.navigation_entry
        entry.name = 'Name'
        entry.description = 'Description'
        
        entry.save()
        
        initial = view.get_initial()
        
        self.assertEqual(initial['name'], 'Name')
        self.assertEqual(initial['description'], 'Description')
    
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        navigation = view.taxon_profiles_navigation
        
        post_data = {
            'input_language': self.meta_app.primary_language,
            'name': 'Name',
            'description': 'Description',
        }

        form = view.form_class(data=post_data)
        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertTrue(response.context_data['success'])
        
        nav_entry = TaxonProfilesNavigationEntry.objects.filter(navigation=navigation).order_by('pk').last()
        
        self.assertEqual(nav_entry.name, post_data['name'])
        self.assertEqual(nav_entry.description, post_data['description'])



class WithTaxonProfilesNavigationEntry:
    
    def setUp(self, *args, **kwargs):
        super().setUp(*args, *kwargs)
        
        self.navigation = TaxonProfilesNavigation(
            taxon_profiles=self.generic_content,
        )
        
        self.navigation.save()
        
        self.navigation_entry = TaxonProfilesNavigationEntry(
            navigation=self.navigation,
        )
        
        self.navigation_entry.save()


class TestCreateTaxonProfilesNavigationEntryChild(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    url_name = 'create_taxonprofiles_navigation_entry'
    view_class = ManageTaxonProfilesNavigationEntry

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'parent_navigation_entry_id': self.navigation_entry.id,
        }
        return url_kwargs
    
    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.set_instances(**view.kwargs)
        
        self.assertEqual(view.taxon_profiles, self.generic_content)
        
        nav_query = TaxonProfilesNavigation.objects.filter(taxon_profiles=self.generic_content)
        
        self.assertTrue(nav_query.exists())
        
        self.assertEqual(view.navigation_entry, None)
        self.assertEqual(view.parent_navigation_entry, self.navigation_entry)
        
        
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        self.assertEqual(context['navigation_entry'], None)
        self.assertEqual(context['parent_navigation_entry'], self.navigation_entry)
        self.assertEqual(context['success'], False)
        self.assertEqual(context['taxon_success'], False)
        
        
    @test_settings
    def test_set_navigation_entry(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        self.assertEqual(view.navigation_entry, None)
        view.set_navigation_entry()
        
        self.assertEqual(view.navigation_entry.parent, self.navigation_entry)
        
        
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        post_data = {
            'input_language': self.meta_app.primary_language,
            'name': 'Name',
            'description': 'Description',
        }

        form = view.form_class(data=post_data)
        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertTrue(response.context_data['success'])
        
        nav_entry = response.context_data['navigation_entry']
        
        self.assertEqual(nav_entry.parent, self.navigation_entry)
        self.assertEqual(nav_entry.name, post_data['name'])
        self.assertEqual(nav_entry.description, post_data['description'])
        

class TestManageTaxonProfilesNavigationEntry(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    url_name = 'manage_taxonprofiles_navigation_entry'
    view_class = ManageTaxonProfilesNavigationEntry

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'navigation_entry_id': self.navigation_entry.id,
        }
        return url_kwargs
    
    
    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.set_instances(**view.kwargs)
        
        self.assertEqual(view.taxon_profiles, self.generic_content)
        
        nav_query = TaxonProfilesNavigation.objects.filter(taxon_profiles=self.generic_content)
        
        self.assertTrue(nav_query.exists())
        
        self.assertEqual(view.navigation_entry, self.navigation_entry)
        self.assertEqual(view.parent_navigation_entry, None)
        
        
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        self.assertEqual(context['navigation_entry'], self.navigation_entry)
        self.assertEqual(context['parent_navigation_entry'], None)
        self.assertEqual(context['success'], False)
        self.assertEqual(context['taxon_success'], False)
        
        
    @test_settings
    def test_set_navigation_entry(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        view.set_navigation_entry()
        self.assertEqual(view.navigation_entry, self.navigation_entry)
    
    

class TestAddTaxonProfilesNavigationEntryTaxon(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    url_name = 'create_taxonprofiles_navigation_entry_taxon'
    view_class = AddTaxonProfilesNavigationEntryTaxon
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
        }
        return url_kwargs
    
    @test_settings
    def test_get_form_kwargs(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        form_kwargs = view.get_form_kwargs()
        
        self.assertEqual(form_kwargs['parent'], None)
        self.assertEqual(form_kwargs['navigation_entry'], None)
        self.assertEqual(form_kwargs['taxon_search_url'], reverse('search_taxon'))
        
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        taxon = LazyTaxon(instance=chordata_db)
        
        post_data = {
            'taxon_0' : taxon.taxon_source,
            'taxon_1' : taxon.taxon_latname,
            'taxon_2' : taxon.taxon_author,
            'taxon_3' : str(taxon.name_uuid),
            'taxon_4' : taxon.taxon_nuid,
        }

        form = view.form_class(data=post_data, **view.get_form_kwargs())
        is_valid = form.is_valid()

        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.context_data['taxon_success'], True)
        
        taxon_link = TaxonProfilesNavigationEntryTaxa.objects.filter().order_by('pk').last()
        
        self.assertEqual(taxon_link.navigation_entry, response.context_data['navigation_entry'])
        
        self.assertEqual(taxon_link.name_uuid, taxon.name_uuid)


class TestAddTaxonProfilesNavigationEntryTaxonExistingEntry(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    url_name = 'add_taxonprofiles_navigation_entry_taxon'
    view_class = AddTaxonProfilesNavigationEntryTaxon
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'navigation_entry_id': self.navigation_entry.id,
        }
        return url_kwargs
    
    @test_settings
    def test_get_form_kwargs(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        form_kwargs = view.get_form_kwargs()
        
        self.assertEqual(form_kwargs['parent'], None)
        self.assertEqual(form_kwargs['navigation_entry'], self.navigation_entry)
        self.assertEqual(form_kwargs['taxon_search_url'], reverse('search_taxon'))


class TestAddTaxonProfilesNavigationEntryTaxonParent(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    url_name = 'create_taxonprofiles_navigation_entry_taxon'
    view_class = AddTaxonProfilesNavigationEntryTaxon
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
            'parent_navigation_entry_id': self.navigation_entry.id,
        }
        return url_kwargs
    
    @test_settings
    def test_get_form_kwargs(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        form_kwargs = view.get_form_kwargs()
        
        self.assertEqual(form_kwargs['parent'], self.navigation_entry)
        self.assertEqual(form_kwargs['navigation_entry'], None)
        self.assertEqual(form_kwargs['taxon_search_url'], reverse('search_taxon'))
        

class TestDeleteTaxonProfilesNavigationEntry(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    url_name = 'delete_taxonprofiles_navigation_entry'
    view_class = DeleteTaxonProfilesNavigationEntry
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'pk' : self.navigation_entry.id,
        }
        return url_kwargs
    
    
    @test_settings
    def test_form_valid(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.object = view.get_object()
        
        response = view.form_valid(None)
        
        self.assertEqual(response.context_data['navigation_entry_id'], self.navigation_entry.id)
        self.assertEqual(response.context_data['taxon_profiles'], self.generic_content)
        self.assertEqual(response.context_data['deleted'], True)
        
        exists_qry = TaxonProfilesNavigationEntry.objects.filter(pk=self.navigation_entry.id)
        self.assertFalse(exists_qry.exists())
        

class TestGetTaxonProfilesNavigation(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    url_name = 'get_taxonprofiles_navigation'
    view_class = GetTaxonProfilesNavigation
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id' : self.generic_content.id,
        }
        return url_kwargs
    
    
    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.set_instances(**view.kwargs)
        self.assertEqual(view.taxon_profiles_navigation, self.navigation)
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        self.assertEqual(self.navigation.prerendered, None)
        self.assertEqual(self.navigation.last_prerendered_at, None)
        
        context = view.get_context_data(**view.kwargs)
        
        ctype = ContentType.objects.get_for_model(TaxonProfilesNavigationEntry)
        
        self.assertEqual(context['taxon_profiles_navigation'], self.navigation)
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        self.assertEqual(context['navigation_entry_content_type'], ctype)
        
        self.navigation.refresh_from_db()
        self.assertTrue(self.navigation.prerendered != None)
        
        

class TestManageNavigationImage(ContentImagePostData, WithImageStore, WithMedia, WithTaxonProfilesNavigationEntry,
        WithTaxonProfiles, WithFormTest, ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp,
        WithTenantClient, TenantTestCase):
    
    url_name = 'manage_taxon_profiles_navigation_image'
    view_class = ManageNavigationImage
    
    def get_url_kwargs(self):

        navigation_entry_content_type = ContentType.objects.get_for_model(TaxonProfilesNavigationEntry)

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : navigation_entry_content_type.id,
            'object_id': self.navigation_entry.id,
        }
        return url_kwargs
    
    
    @test_settings
    def test_save_image(self):
        
        navigation_entry_content_type = ContentType.objects.get_for_model(TaxonProfilesNavigationEntry)

        view = self.get_view()
        view.meta_app = self.meta_app
        view.content_image = None
        view.taxon = None
        view.object_content_type = navigation_entry_content_type
        view.content_instance = self.navigation_entry
        post_data, post_files = self.get_post_form_data()
        
        form = view.form_class(data=post_data, files=post_files)
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        previously_modified_at = self.navigation.last_modified_at
        
        view.save_image(form)
        
        self.navigation.refresh_from_db()
        
        delta = previously_modified_at - self.navigation.last_modified_at
        
        self.assertTrue(delta.total_seconds() < 0)
        
    
    @test_settings
    def test_get_context_data(self):
        
        navigation_entry_content_type = ContentType.objects.get_for_model(TaxonProfilesNavigationEntry)

        view = self.get_view()
        view.meta_app = self.meta_app
        view.content_image = None
        view.taxon = None
        view.object_content_type = navigation_entry_content_type
        view.content_instance = self.navigation_entry
        view.image_type = 'image'
        view.new = True
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon_profiles'], self.generic_content)


class TestDeleteNavigationImage(WithImageStore, WithMedia, WithTaxonProfilesNavigationEntry,
        WithTaxonProfiles, WithFormTest, ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp,
        WithTenantClient, TenantTestCase):
    
    url_name = 'delete_taxon_profiles_navigation_image'
    view_class = DeleteNavigationImage
    
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        
        image_store = self.create_image_store()
        self.content_type = ContentType.objects.get_for_model(TaxonProfilesNavigationEntry)
        
        self.content_image = ContentImage(
            image_store=image_store,
            content_type=self.content_type,
            object_id=self.navigation_entry.id,
            image_type='image',
        )

        self.content_image.save()
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'pk' : self.content_image.id,
        }
        return url_kwargs
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.object = self.content_image
        
        previously_modified_at = self.navigation.last_modified_at

        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        
        self.navigation.refresh_from_db()
        
        self.assertEqual(previously_modified_at, self.navigation.last_modified_at)
        
    @test_settings
    def test_get_context_data_post(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.object = self.content_image
        view.request.method = 'POST'
        
        previously_modified_at = self.navigation.last_modified_at

        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        
        self.navigation.refresh_from_db()
        
        delta = previously_modified_at - self.navigation.last_modified_at
        
        self.assertTrue(delta.total_seconds() < 0)
        
        

class TestDeleteTaxonProfilesNavigationEntryTaxon(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    url_name = 'delete_taxonprofiles_navigation_entry_taxon'
    view_class = DeleteTaxonProfilesNavigationEntryTaxon
    
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        taxon = LazyTaxon(instance=chordata_db)
        
        self.navigation_entry_taxon = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=self.navigation_entry,
        )
        
        self.navigation_entry_taxon.set_taxon(taxon)
        
        self.navigation_entry_taxon.save()
        
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'pk' : self.navigation_entry_taxon.id,
        }
        return url_kwargs
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.object = self.navigation_entry_taxon
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['navigation_entry'], self.navigation_entry)
        self.assertEqual(context['taxon_profiles'], self.generic_content)
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.object = self.navigation_entry_taxon
        
        previously_modified_at = self.navigation.last_modified_at
        
        deleted_pk = self.navigation_entry_taxon.id
        
        response = view.form_valid(None)
        
        self.assertTrue(response.context_data['deleted'])
        self.assertEqual(response.context_data['navigation_entry_taxon_id'], deleted_pk)
        
        self.navigation.refresh_from_db()
        
        delta = previously_modified_at - self.navigation.last_modified_at
        
        self.assertTrue(delta.total_seconds() < 0)
        
        
class TestChangeNavigationEntryPublicationStatus(WithTaxonProfilesNavigationEntry, WithTaxonProfiles,
        ViewTestMixin, WithAjaxAdminOnly,  WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):
    
    
    
    url_name = 'change_taxonprofiles_navigation_entry_publication_status'
    view_class = ChangeNavigationEntryPublicationStatus
    
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        taxon = LazyTaxon(instance=chordata_db)
        
        self.navigation_entry_taxon = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=self.navigation_entry,
        )
        
        self.navigation_entry_taxon.set_taxon(taxon)
        
        self.navigation_entry_taxon.save()
        
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id': self.generic_content.id,
            'navigation_entry_id' : self.navigation_entry.id,
        }
        return url_kwargs
    
    @test_settings
    def test_set_navigation_entry(self):
        
        view = self.get_view()
        
        view.set_navigation_entry(**view.kwargs)
        view.meta_app = self.meta_app
        
        self.assertEqual(view.taxon_profiles, self.generic_content)
        self.assertEqual(view.navigation_entry, self.navigation_entry)
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.set_navigation_entry(**view.kwargs)
        view.meta_app = self.meta_app
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['success'], False)
        self.assertEqual(context['navigation_entry'], self.navigation_entry)
        self.assertEqual(context['taxon_profiles'], self.generic_content)
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        view.set_navigation_entry(**view.kwargs)
        view.meta_app = self.meta_app
        
        initial = view.get_initial()
        
        self.assertEqual(initial['publication_status'], 'publish')
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        view.set_navigation_entry(**view.kwargs)
        view.meta_app = self.meta_app
        
        post_data = {
            'publication_status': 'draft',
        }
        
        form = view.form_class(data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        
        self.navigation_entry.refresh_from_db()
        
        self.assertEqual(self.navigation_entry.publication_status, 'draft')
        



class TestCreateTaxonTextTypeCategory(WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'create_taxon_text_type_category'
    view_class = ManageTaxonTextTypeCategory


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
    
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id': self.generic_content.id,
            'taxon_profile_id' : self.taxon_profile.id,
        }
        return url_kwargs
    
    @test_settings
    def test_set_category(self):
        
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        self.assertEqual(view.taxon_profiles, self.generic_content)
        self.assertEqual(view.taxon_profile, self.taxon_profile)
        self.assertEqual(view.category, None)
    
    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        self.assertEqual(context['taxon_profile'], self.taxon_profile)
        self.assertEqual(context['category'], None)
        self.assertEqual(context['success'], False)
        self.assertEqual(context['created'], False)
    
    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        initial = view.get_initial()
        self.assertEqual(initial['taxon_profiles'], self.generic_content)
    
    @test_settings
    def test_get_form(self):
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        form = view.get_form()
        
        self.assertEqual(form.__class__, view.form_class)
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        test_name = 'test category'
        
        exists_qry = TaxonTextTypeCategory.objects.filter(name=test_name)
        
        post_data = {
            'name' : test_name,
            'taxon_profiles': self.generic_content.id,
            'input_language': self.meta_app.primary_language,
        }
        
        form = view.form_class(data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        self.assertFalse(exists_qry.exists())
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['created'], True)
        
        self.assertTrue(exists_qry.exists())
        
        
    
    
    
class TestManageTaxonTextTypeCategory(WithTaxonProfile, WithTaxonProfiles, ViewTestMixin, WithAjaxAdminOnly,
        WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):
    
    url_name = 'manage_taxon_text_type_category'
    view_class = ManageTaxonTextTypeCategory
    
    def setUp(self):
        super().setUp()
        
        self.category = TaxonTextTypeCategory(
            taxon_profiles=self.generic_content,
            name = 'Test Category',
        )
        
        self.category.save()
    
    
    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
    
    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_profiles_id': self.generic_content.id,
            'taxon_profile_id' : self.taxon_profile.id,
            'taxon_text_type_category_id': self.category.id,
        }
        return url_kwargs
    
    
    @test_settings
    def test_set_category(self):
        
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        self.assertEqual(view.taxon_profiles, self.generic_content)
        self.assertEqual(view.taxon_profile, self.taxon_profile)
        self.assertEqual(view.category, self.category)
    
    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon_profiles'], self.generic_content)
        self.assertEqual(context['taxon_profile'], self.taxon_profile)
        self.assertEqual(context['category'], self.category)
        self.assertEqual(context['success'], False)
        self.assertEqual(context['created'], False)
    
    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        initial = view.get_initial()
        self.assertEqual(initial['taxon_profiles'], self.generic_content)
    
    @test_settings
    def test_get_form(self):
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        form = view.get_form()
        
        self.assertEqual(form.__class__, view.form_class)
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        view.set_category(**view.kwargs)
        
        test_name = 'test category changed'
                
        post_data = {
            'name' : test_name,
            'taxon_profiles': self.generic_content.id,
            'input_language': self.meta_app.primary_language,
        }
        
        form = view.form_class(data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['created'], False)
        
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, test_name)
        
class TestDeleteTaxonTextTypeCategory(WithTaxonProfile, WithTaxonProfiles, ViewTestMixin,
                WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_taxon_text_type_category'
    view_class = DeleteTaxonTextTypeCategory


    def setUp(self):
        super().setUp()
        self.category = TaxonTextTypeCategory(
            taxon_profiles=self.generic_content,
            name = 'Test Category',
        )
        
        self.category.save()


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'taxon_profile_id': self.taxon_profile.id,
            'pk' : self.category.id,
        }
        return url_kwargs
from django.conf import settings
from django.test import RequestFactory
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.contenttypes.models import ContentType

from django.db import connection


from app_kit.tests.common import (test_settings, TESTS_ROOT, powersetdic, TEST_MEDIA_ROOT, TEST_IMAGE_PATH)
from app_kit.models import (MetaApp, MetaAppGenericContent, ImageStore, ContentImage)
from app_kit.features.backbonetaxonomy.models import BackboneTaxa

from app_kit.multi_tenancy.models import TenantUserRole

from app_kit.settings import ADDABLE_FEATURES, REQUIRED_FEATURES

from app_kit.utils import import_module

from app_kit.appbuilder import AppPreviewBuilder

from taxonomy.models import TaxonomyModelRouter, MetaVernacularNames
from taxonomy.lazy import LazyTaxon

from localcosmos_server.models import App, SecondaryAppLanguages

from django.utils import timezone

import os, shutil, hashlib
from PIL import Image

from django_tenants.test.client import TenantClient

from django_tenants.utils import get_tenant_domain_model, get_tenant_model
Tenant = get_tenant_model()
Domain = get_tenant_domain_model()


class WithLoggedInUser:
    
    def setUp(self):
        super().setUp()

        self.user = self.create_user()
        self.tenant_client.login(username=self.user.username, password=self.test_password)


    def make_user_tenant_admin(self, user, tenant):

        role = TenantUserRole.objects.filter(user=user, tenant=tenant).first()

        if not role:
            role = TenantUserRole(user=user, tenant=tenant)

        role.role='admin'
        role.save()
                    
        
class WithTenantClient:

    def setUp(self):
        super().setUp()

        self.superuser = self.create_superuser()
        self.tenant_client = TenantClient(self.tenant)


class WithUser:

    # allowed special chars; @/./+/-/_
    test_username = 'TestUser@.+-_'
    test_email = 'testuser@localcosmos.org'
    test_password = '#$_><*}{|///0x'

    test_superuser_username = 'TestSuperuser'
    test_superuser_email = 'testsuperuser@localcosmos.org'

    test_first_name = 'First Name'

    def create_user(self):
        user = User.objects.filter(username=self.test_username).first()
        if not user:
            user = User.objects.create_user(self.test_username, self.test_email, self.test_password)
        return user

    def create_superuser(self):
        superuser = User.objects.filter(is_superuser=True).first()
        if not superuser:
            superuser = User.objects.create_superuser(self.test_superuser_username, self.test_superuser_email,
                                                      self.test_password)
        return superuser
        



# creating a meta app version creates files on disk
# each method has to be decorated with @test_settings
class WithMetaApp:

    domain_name = 'testmetaapp.my-domain.com'
    name = 'Test Meta App'
    primary_language = 'en'
    subdomain = 'testmetaapp'

    @test_settings
    def setUp(self):
        super().setUp()

        self.assertTrue(settings.APP_KIT_ROOT.startswith(TESTS_ROOT))

        # creates App and MetaApp
        self.meta_app = MetaApp.objects.all().first()

        if not self.meta_app:
            app = App.objects.filter(uid=self.subdomain).first()
            if app:
                app.delete()
                
            self.meta_app = MetaApp.objects.create(self.name, self.primary_language, self.domain_name,
                                                   self.tenant, self.subdomain)
        

    @test_settings
    def tearDown(self):
        if not settings.APP_KIT_ROOT.startswith(TESTS_ROOT):
            raise ValueError('Invalid APP_KIT_ROOT setting: {1}. Does not start with: {2}'.format(
                settings.APP_KIT_ROOT, TESTS_ROOT))

        if not settings.LOCALCOSMOS_APPS_ROOT.startswith(TESTS_ROOT):
            raise ValueError('Invalid LOCALCOSMOS_APPS_ROOT setting: {1}. Does not start with: {2}'.format(
                settings.LOCALCOSMOS_APPS_ROOT, TESTS_ROOT))
        
        for entry in os.scandir(settings.APP_KIT_ROOT):
            if os.path.isdir(entry.path):
                shutil.rmtree(entry.path)

        for www_entry in os.scandir(settings.LOCALCOSMOS_APPS_ROOT):
            if os.path.isdir(www_entry.path):
                shutil.rmtree(www_entry.path)

        super().tearDown()


    def create_secondary_languages(self, languages):
        
        for language_code in languages:
            if language_code != self.meta_app.primary_language:

                # create the new locale
                secondary_language = SecondaryAppLanguages(
                    app=self.meta_app.app,
                    language_code=language_code,
                )
                secondary_language.save()


    def create_generic_content(self, FeatureModel, meta_app, force=False):

        content_type = ContentType.objects.get_for_model(FeatureModel)

        exists = MetaAppGenericContent.objects.filter(meta_app=meta_app,
                                                    content_type=content_type).exists()


        app_link = None

        if not exists or force == True:
            
            # create link
            generic_content_name = '{0} {1}'.format(meta_app.name, FeatureModel._meta.verbose_name)
            generic_content = FeatureModel.objects.create(generic_content_name, meta_app.primary_language)

            app_link = MetaAppGenericContent(
                meta_app=meta_app,
                content_type=content_type,
                object_id=generic_content.id
            )

            app_link.save()


        return app_link
        

    # create one instance of all generic contents for the given meta_app, if it does not yet exist
    def create_all_generic_contents(self, meta_app):

        
        for feature_module in ADDABLE_FEATURES:

            module = import_module(feature_module)

            FeatureModel = module.models.FeatureModel

            app_link = self.create_generic_content(FeatureModel, meta_app)


    def get_generic_content_link(self, Model):

        content_type = ContentType.objects.get_for_model(Model)
        
        link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=content_type)

        return link


    def create_content_image(self, content_instance, user, taxon=None, image_type='image', image_store=None):

        image_name = '{0}-{1}.jpg'.format(content_instance.__class__.__name__, content_instance.id)

        md5 = hashlib.md5(Image.open(TEST_IMAGE_PATH).tobytes()).hexdigest()

        if not image_store:
            image_store = ImageStore.objects.filter(md5=md5).first()

            if not image_store:

                image = SimpleUploadedFile(name=image_name, content=open(TEST_IMAGE_PATH, 'rb').read(),
                                                content_type='image/jpeg')

                image_store = ImageStore(
                    source_image=image,
                    uploaded_by=user,
                    md5=md5,
                    taxon=taxon,
                )

                image_store.save()

        content_type = ContentType.objects.get_for_model(content_instance)

        content_image = ContentImage.objects.filter(image_store=image_store, content_type=content_type,
                                                    object_id=content_instance.id, image_type=image_type).first()

        if not content_image:

            content_image = ContentImage(
                image_store=image_store,
                content_type=content_type,
                object_id=content_instance.id,
                image_type=image_type,
            )

            content_image.save()

        return content_image


    def build_app_preview(self):

        preview_builder = AppPreviewBuilder(self.meta_app)
        preview_builder.build()


class WithMedia:

    def clean_media(self):

        images = ImageStore.objects.all()
        images.delete()
        
        if os.path.isdir(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)

        os.makedirs(TEST_MEDIA_ROOT)  

    
    def setUp(self):
        super().setUp()
        self.clean_media()
    
    
    def tearDown(self):
        super().tearDown()
        self.clean_media()



class WithZipFile:

    def get_zip_file(self):

        zip_file = SimpleUploadedFile(
            "importfile.zip",
            b"these are the file contents!"
        )

        return zip_file


class WithImageStore:

    def create_image_store(self, name='test_image.jpg', test_image_path=TEST_IMAGE_PATH):

        user = self.create_user()

        content_type='image/jpeg'

        if test_image_path.endswith('.svg'):
            md5 = hashlib.md5(open(test_image_path,'rb').read()).hexdigest()
            content_type='image/svg'
            name = os.path.basename(test_image_path)
        else:
            md5 = hashlib.md5(Image.open(test_image_path).tobytes()).hexdigest()

        image = SimpleUploadedFile(name=name, content=open(test_image_path, 'rb').read(),
                                        content_type=content_type)

        image_store = ImageStore(
            source_image=image,
            uploaded_by=user,
            md5=md5,
            taxon=None,
        )

        image_store.save()

        return image_store
        

    def create_image_store_with_taxon(self, lazy_taxon=None):

        user = self.create_user()
        md5 = hashlib.md5(Image.open(TEST_IMAGE_PATH).tobytes()).hexdigest()

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        models = TaxonomyModelRouter('taxonomy.sources.col')

        # first, add a single backbone taxon
        if lazy_taxon == None:
            lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
            lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        image_store = ImageStore(
            source_image=image,
            uploaded_by=user,
            md5=md5,
            taxon=lazy_taxon,
        )

        image_store.save()

        return image_store
        


from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from content_licencing.licences import LICENCE_CHOICES, DEFAULT_LICENCE

class WithFormTest:

    def get_licencing_post_data(self):

        licencing_data = {
            'creator_name' : 'James Bond',
            'creator_link' : 'https://bond.org',
            'source_link' : 'https://bond.org/james.jpg',
            'licence_0' : 'CC0',
            'licence_1' : '1.0',
        }

        return licencing_data


    def perform_form_test(self, FormClass, post_data, form_kwargs={}, file_data={}, required_fields=[],
                          form_args=[]):

        if not required_fields:
            required_fields = []

        form = FormClass(*form_args, **form_kwargs)

        # support multivaluefields
        for field in form:

            if field.field.required == True:
                if hasattr(field.field, 'fields'):
                    for counter, subfield in enumerate(field.field.fields, 0):
                        required_fields.append('{0}_{1}'.format(field.name, counter))
                else:
                    required_fields.append(field.name)
                    
        required_fields = set(required_fields)

        post_and_files = {}
        post_and_files.update(post_data.copy())

        if file_data:
            post_and_files.update(file_data.copy())
        
        testcases = powersetdic(post_and_files)
        print('testing {0} possibilities'.format(len(testcases)))

        for post in testcases:

            data = {}
            files = {}
            
            for key, value in post.items():

                if key in post_data:
                    data[key] = value
                else:
                    files[key] = file_data[key]()

            if files:
                form = FormClass(*form_args, data=data, files=files, **form_kwargs)
                keys = set(data.keys()).union(set(files.keys()))
            else:
                form = FormClass(*form_args, data=data, **form_kwargs)
                keys = set(data.keys())

            is_valid = form.is_valid()
            
            if required_fields.issubset(keys):                    
                self.assertEqual(form.errors, {})
                self.assertTrue(is_valid)
            else:                    
                self.assertFalse(is_valid)


    def get_image(self, filename='test_image.jpg'):

        im = Image.new(mode='RGB', size=(200, 200)) # create a new image using PIL
        im_io = BytesIO() # a BytesIO object for saving image
        im.save(im_io, 'JPEG') # save the image to im_io
        im_io.seek(0) # seek to the beginning

        image = InMemoryUploadedFile(
            im_io, None, filename, 'image/jpeg', len(im_io.getvalue()), None
        )

        return image


class WithAjaxAdminOnly:

    def before_test_dispatch(self):
        pass

    @test_settings
    def test_dispatch(self):

        self.before_test_dispatch()

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
 

class WithAdminOnly:

    def before_test_dispatch(self):
        pass

    @test_settings
    def test_dispatch(self):

        self.before_test_dispatch()

        url = self.get_url()
        
        url_kwargs = {}

        response = self.tenant_client.get(url, **url_kwargs)
        self.assertEqual(response.status_code, 403)

        # test with admin role
        self.make_user_tenant_admin(self.user, self.tenant)
        response = self.tenant_client.get(url, **url_kwargs)
        self.assertEqual(response.status_code, 200)



class WithPublicDomain:
    
    def create_public_domain(self):
        
        connection.set_schema_to_public()

        public_schema = Tenant(
            schema_name = 'public',
        )
        public_schema.save()

        domain = Domain(
            domain='test.org',
            tenant=public_schema,
        )

        domain.save()

        connection.set_tenant(self.tenant)
        
        
class ViewTestMixin(WithPublicDomain):

    def get_url_kwargs(self):
        return {}

    def get_url(self):
        url_kwargs = self.get_url_kwargs()
        url = reverse(self.url_name, kwargs=url_kwargs)
        return url

    def get_request(self, ajax=False):
        factory = RequestFactory()
        url = self.get_url()

        if ajax == True:
            url_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }
            request = factory.get(url, **url_kwargs)
        else:
            request = factory.get(url)
        request.user = self.user
        request.session = self.client.session
        request.tenant = self.tenant

        return request

    def get_view(self, ajax=False):

        request = self.get_request(ajax=ajax)

        view = self.view_class()        
        view.request = request
        view.kwargs = self.get_url_kwargs()

        return view


class MultipleURLSViewTestMixin(WithPublicDomain):

    def get_url_kwargs_list(self):
        return []

    def get_urls(self):

        urls = []

        url_kwargs_list = self.get_url_kwargs_list()

        for url_kwargs in url_kwargs_list:
        
            url = reverse(self.url_name, kwargs=url_kwargs)

            url_dict = {
                'url' : url,
                'url_kwargs' : url_kwargs,
            }

            urls.append(url_dict)

        return urls


    def get_url(self):
        urls = self.get_urls()
        return urls[0]['url']

    def get_requests(self, ajax=False):

        factory = RequestFactory()

        requests = []

        urls = self.get_urls()

        for url_dict in urls:

            if ajax == True:
                ajax_kwargs = {
                    'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
                }
                request = factory.get(url_dict['url'], **ajax_kwargs)
            else:
                request = factory.get(url_dict['url'])

            request.user = self.user
            request.session = self.client.session
            request.tenant = self.tenant
            request.url_kwargs = url_dict['url_kwargs']

            requests.append(request)

        return requests

    def get_views(self, ajax=False):

        views = []

        requests = self.get_requests(ajax=ajax)

        for request in requests:

            view = self.view_class()        
            view.request = request
            view.kwargs = request.url_kwargs

            views.append(view)

        return views



class WithMetaVernacularNames:
    
    def create_mvn(self, taxon, name, language):
        
        backbonetaxonomy = self.meta_app.backbone()
        
        mvn = MetaVernacularNames(
            taxon_source = taxon.taxon_source,
            taxon_latname = taxon.taxon_latname,
            taxon_author = taxon.taxon_author,
            taxon_nuid = taxon.taxon_nuid,
            name_uuid = taxon.name_uuid,
            language = language,
            name = name,
        )
        
        mvn.save()
        
        backbone_taxon = BackboneTaxa.objects.filter(name_uuid=taxon.name_uuid).first()
        
        if not backbone_taxon:
            backbone_taxon = BackboneTaxa(
                backbonetaxonomy = backbonetaxonomy,
            )
            
            backbone_taxon.set_taxon(self.taxon)
            
            backbone_taxon.save()
        
        return mvn
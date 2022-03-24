from django.test import TestCase, RequestFactory
from django.conf import settings

from app_kit.models import App, LCFramework
from app_kit.framework.altruistic.AppBuilder import AppBuilder as AppBuilderAltruistic

from app_kit.models import BackboneTaxonomyFeature
from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa
from taxonomy.models import Taxon

from django.contrib.contenttypes.models import ContentType

import os, shutil

class TestAppFramework(TestCase):
    
    def setUp(self, framework):
        # create an app
        self.app = App.objects.create("testapp", "en", framework)

    def tearDown(self):
        # remove the app folder if present
        if os.path.isdir(self.app.root_folder()):
            for root, dirs, files in os.walk(self.app.root_folder()):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))

                shutil.rmtree(root)


class TestAltruistic(TestAppFramework):

    AppBuilder = AppBuilderAltruistic

    def setUp(self):
        self.framework = LCFramework(
            name = "Altrustic Albatros",
            folder = "altruistic",
            version = 1,
            status = "development",
        )

        self.framework.save()
        super().setUp(self.framework)


    def test_cordova_create(self):
        builder = self.AppBuilder(self.app)
        builder.create_cordova()


    # Test the deployment of the backbone taxonomy for both webapp and app
    def test_build_BackboneTaxonomy(self):
        # the backbone is present after building the app
        content_type = ContentType.objects.get_for_model(BackboneTaxonomyFeature)
        backbone_feature = AppToFeature.objects.filter(app=self.app, content_type=content_type).first().feature

        backbone = backbone_feature.backbone()

        animalia = Taxon.objects.get(latname="Plantae")

        link = BackboneTaxa(
            backbonetaxonomy = backbone,
            taxon = animalia,
            include_descendants = True,
        )

        link.save()

        builder = self.AppBuilder(self.app)
        builder.build_BackboneTaxonomyFeature(backbone_feature)


    def test_build_BackboneTaxonomy_fulltree(self):
        pass
    



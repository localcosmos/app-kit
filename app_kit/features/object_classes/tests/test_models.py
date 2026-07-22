from django.contrib.contenttypes.models import ContentType
from django_tenants.test.cases import TenantTestCase

from app_kit.features.object_classes.models import ObjectClasses, ObjectClass, ObjectClassTaxon
from app_kit.models import MetaAppGenericContent
from app_kit.tests.common import test_settings
from app_kit.tests.mixins import WithMetaApp

from taxonomy.lazy import LazyTaxon, LazyTaxonList
from taxonomy.models import TaxonomyModelRouter


class WithObjectClasses(WithMetaApp):

	def setUp(self):
		super().setUp()

		self.content_type = ContentType.objects.get_for_model(ObjectClasses)
		self.object_classes_link = self.create_generic_content(ObjectClasses, self.meta_app)
		self.object_classes = self.object_classes_link.generic_content

	def create_object_class(self, name, description=None):

		scientific_name = name.lower().replace(' ', '_')

		object_class = ObjectClass.objects.create(
			object_classes=self.object_classes,
			name=name,
			scientific_name=scientific_name,
			description=description,
		)

		return object_class

	def create_object_class_taxon(self, object_class, taxon):

		object_class_taxon = ObjectClassTaxon(
			object_class=object_class,
		)
		object_class_taxon.set_taxon(taxon)
		object_class_taxon.save()

		return object_class_taxon


class TestObjectClasses(WithObjectClasses, TenantTestCase):

	@test_settings
	def test_taxa(self):

		taxa = self.object_classes.taxa()
		self.assertTrue(isinstance(taxa, LazyTaxonList))
		self.assertEqual(taxa.count(), 0)

		models = TaxonomyModelRouter('taxonomy.sources.col')

		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
		quercus_db = models.TaxonTreeModel.objects.get(taxon_latname='Quercus')
		quercus = LazyTaxon(instance=quercus_db)
		quercus.taxon_include_descendants = True

		lacerta_agilis_class = self.create_object_class('Lacerta agilis class')
		quercus_class = self.create_object_class('Quercus class')

		self.create_object_class_taxon(lacerta_agilis_class, lacerta_agilis)
		self.create_object_class_taxon(quercus_class, quercus)

		taxa = self.object_classes.taxa()

		self.assertTrue(isinstance(taxa, LazyTaxonList))
		self.assertEqual(taxa.count(), 2)
		self.assertEqual({taxon.name_uuid for taxon in taxa}, {lacerta_agilis.name_uuid, quercus.name_uuid})


	@test_settings
	def test_higher_taxa(self):

		higher_taxa = self.object_classes.higher_taxa()
		self.assertTrue(isinstance(higher_taxa, LazyTaxonList))
		self.assertEqual(higher_taxa.count(), 0)

		models = TaxonomyModelRouter('taxonomy.sources.col')

		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
		quercus_db = models.TaxonTreeModel.objects.get(taxon_latname='Quercus')
		quercus = LazyTaxon(instance=quercus_db)
		quercus.taxon_include_descendants = True

		lacerta_agilis_class = self.create_object_class('Lacerta agilis class')
		quercus_class = self.create_object_class('Quercus class')

		self.create_object_class_taxon(lacerta_agilis_class, lacerta_agilis)
		self.create_object_class_taxon(quercus_class, quercus)

		higher_taxa = self.object_classes.higher_taxa()

		self.assertTrue(isinstance(higher_taxa, LazyTaxonList))
		self.assertEqual(higher_taxa.count(), 1)
		self.assertEqual(higher_taxa[0].name_uuid, quercus.name_uuid)


class TestObjectClass(WithObjectClasses, TenantTestCase):

	@test_settings
	def test_create(self):

		models = TaxonomyModelRouter('taxonomy.sources.col')

		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)

		name = 'Lacerta agilis class'
		description = 'Test object class description'
		object_class = self.create_object_class(name, description=description)

		self.assertEqual(object_class.object_classes, self.object_classes)
		self.assertEqual(object_class.name, name)
		self.assertEqual(object_class.scientific_name, 'lacerta_agilis_class')
		self.assertEqual(object_class.description, description)


	@test_settings
	def test_str(self):

		models = TaxonomyModelRouter('taxonomy.sources.col')

		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)

		name = 'Lacerta agilis class'
		object_class = self.create_object_class(name)

		self.assertEqual(str(object_class), name)


	@test_settings
	def test_manager_create(self):

		object_class = ObjectClass.objects.create(
			object_classes=self.object_classes,
			name='Manager class',
			scientific_name='manager_class',
			description='Created with manager',
		)

		self.assertEqual(object_class.object_classes, self.object_classes)
		self.assertEqual(object_class.name, 'Manager class')
		self.assertEqual(object_class.scientific_name, 'manager_class')
		self.assertEqual(object_class.description, 'Created with manager')


	@test_settings
	def test_taxa_property(self):

		models = TaxonomyModelRouter('taxonomy.sources.col')

		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)

		object_class = self.create_object_class('Lacerta agilis class')
		self.create_object_class_taxon(object_class, lacerta_agilis)

		taxa = object_class.taxa
		self.assertEqual(taxa.count(), 1)
		self.assertEqual(taxa.first().name_uuid, lacerta_agilis.name_uuid)


	@test_settings
	def test_is_taxon_compatible_exact_match(self):

		models = TaxonomyModelRouter('taxonomy.sources.col')

		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)

		object_class = self.create_object_class('Lacerta agilis class')
		self.create_object_class_taxon(object_class, lacerta_agilis)

		self.assertTrue(object_class.is_taxon_compatible(lacerta_agilis))


	@test_settings
	def test_is_taxon_compatible_ancestor_match(self):

		models = TaxonomyModelRouter('taxonomy.sources.col')

		quercus_db = models.TaxonTreeModel.objects.get(taxon_latname='Quercus')
		quercus = LazyTaxon(instance=quercus_db)
		quercus_robur_db = models.TaxonTreeModel.objects.get(taxon_latname='Quercus robur')
		quercus_robur = LazyTaxon(instance=quercus_robur_db)

		object_class = self.create_object_class('Quercus class')
		self.create_object_class_taxon(object_class, quercus)

		self.assertTrue(object_class.is_taxon_compatible(quercus_robur))


	@test_settings
	def test_is_taxon_compatible_returns_false_for_non_matching_taxon(self):

		models = TaxonomyModelRouter('taxonomy.sources.col')

		quercus_db = models.TaxonTreeModel.objects.get(taxon_latname='Quercus')
		quercus = LazyTaxon(instance=quercus_db)
		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)

		object_class = self.create_object_class('Quercus class')
		self.create_object_class_taxon(object_class, quercus)

		self.assertFalse(object_class.is_taxon_compatible(lacerta_agilis))


class TestObjectClassTaxon(WithObjectClasses, TenantTestCase):

	@test_settings
	def test_create(self):

		models = TaxonomyModelRouter('taxonomy.sources.col')

		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)

		object_class = self.create_object_class('Lacerta agilis class')
		object_class_taxon = self.create_object_class_taxon(object_class, lacerta_agilis)

		self.assertEqual(object_class_taxon.object_class, object_class)
		self.assertEqual(object_class_taxon.taxon_latname, lacerta_agilis.taxon_latname)
		self.assertEqual(object_class_taxon.taxon_source, lacerta_agilis.taxon_source)


	@test_settings
	def test_str(self):

		models = TaxonomyModelRouter('taxonomy.sources.col')

		lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
		lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)

		object_class = self.create_object_class('Lacerta agilis class')
		object_class_taxon = self.create_object_class_taxon(object_class, lacerta_agilis)

		self.assertEqual(str(object_class_taxon), 'Lacerta agilis class - Lacerta agilis')

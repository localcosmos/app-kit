from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType

from app_kit.generic import AppContentTaxonomicRestriction

from app_kit.tests.common import test_settings

from app_kit.features.generic_forms.models import (GenericForm, GenericField, GenericFieldToGenericForm,
        GenericValues, DJANGO_FIELD_WIDGETS, DJANGO_FIELD_CLASSES, DEFAULT_WIDGETS, VALUE_TYPES,
        FIELDCLASS_DATATYPE)

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon


class WithGenericForm:

    def create_generic_form(self):
        generic_form = GenericForm.objects.create('Test Generic Form', 'en')
        return generic_form

    def create_all_fields(self, generic_form):

        created_fields = []
        
        taxon_field = GenericField(
            field_class='TaxonField',
            render_as=DEFAULT_WIDGETS['TaxonField'],
            role='taxonomic_reference',
            label='Taxonomic Reference',
        )
        taxon_field.save(generic_form)
        taxon_field_link = GenericFieldToGenericForm(
            generic_field=taxon_field,
            generic_form=generic_form,
        )
        taxon_field_link.save()

        created_fields.append(taxon_field)

        geo_field = GenericField(
            field_class='PointJSONField',
            render_as=DEFAULT_WIDGETS['PointJSONField'],
            role='geographic_reference',
            label='Geographic Reference',
        )
        geo_field.save(generic_form)
        geo_field_link = GenericFieldToGenericForm(
            generic_field=geo_field,
            generic_form=generic_form,
        )
        geo_field_link.save()

        created_fields.append(geo_field)

        timestamp_field = GenericField(
            field_class='DateTimeJSONField',
            render_as=DEFAULT_WIDGETS['DateTimeJSONField'],
            role='temporal_reference',
            label='Temporal Reference',
        )
        timestamp_field.save(generic_form)
        timestamp_field_link = GenericFieldToGenericForm(
            generic_field=timestamp_field,
            generic_form=generic_form,
        )
        timestamp_field_link.save()

        created_fields.append(timestamp_field)
        

        for tup in DJANGO_FIELD_CLASSES:

            field_class = tup[0]
            name = tup[1]

            if field_class not in ['PointJSONField', 'DateTimeJSONField', 'TaxonField']:

                generic_field = GenericField(
                    field_class=field_class,
                    render_as=DEFAULT_WIDGETS[field_class],
                    role='regular',
                    label=str(name),
                )
                generic_field.save(generic_form)
                
                generic_field_link = GenericFieldToGenericForm(
                    generic_field=generic_field,
                    generic_form=generic_form,
                )
                generic_field_link.save()

                if field_class == 'ChoiceField':

                    for choice in ['choice 1', 'choice 2']:

                        value = GenericValues(
                            generic_field=generic_field,
                            text_value=choice,
                            value_type='choice',
                            name=choice,
                        )

                        value.save()

                elif field_class == 'MultipleChoiceField':

                    for choice in ['muliple choice 1', 'multiple choice 2']:

                        value = GenericValues(
                            generic_field=generic_field,
                            text_value=choice,
                            value_type='choice',
                            name=choice,
                        )

                        value.save()


                created_fields.append(generic_field)


        return created_fields
    

class TestGenericForm(WithGenericForm, TenantTestCase):
    
    @test_settings
    def test_create(self):
        name = 'Test Generic Form'
        language = 'en'
        generic_form = GenericForm.objects.create(name, language)

        generic_form.refresh_from_db()
        self.assertEqual(generic_form.name, name)
        self.assertEqual(generic_form.primary_language, language)


    @test_settings
    def test_get_primary_localization(self):
        generic_form = self.create_generic_form()
        fields = self.create_all_fields(generic_form)

        locale = generic_form.get_primary_localization()

        for field in fields:
            self.assertIn(field.label, locale)
            self.assertEqual(locale[field.label], field.label)

        values = GenericValues.objects.all()
        for value in values:
            self.assertIn(value.name, locale)
            self.assertEqual(locale[value.name], value.name)


    @test_settings
    def test_taxon_query_base(self):
        generic_form = self.create_generic_form()
        fields = self.create_all_fields(generic_form)

        query_base = generic_form._taxon_query_base()
        # how to test Q() ?

    @test_settings
    def test_taxa_and_higher_taxa(self):
        # add same taxon to two fields - only one taxon should be present in taxa
        generic_form = self.create_generic_form()
        fields = self.create_all_fields(generic_form)

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        
        # field 0,1,2 are reference fields and cannot be restricted
        field_1 = fields[3]
        field_2 = fields[4]
        field_3 = fields[5]

        generic_field_content_type = ContentType.objects.get_for_model(GenericField)

        for field in [field_1, field_3]:
            restriction = AppContentTaxonomicRestriction(
                content_type=generic_field_content_type,
                object_id=field.id,
                taxon=lacerta_agilis,
            )

            restriction.save()

        quercus = models.TaxonTreeModel.objects.get(taxon_latname='Quercus')
        quercus = LazyTaxon(instance=quercus)
        quercus.taxon_include_descendants=True
        generic_form_content_type = ContentType.objects.get_for_model(GenericForm)
        restriction_2 = AppContentTaxonomicRestriction(
            content_type=generic_form_content_type,
            object_id=generic_form.id,
            taxon=quercus,
        )
        restriction_2.save()

        taxa = generic_form.taxa()

        expected_taxon_latnames = [quercus.taxon_latname, lacerta_agilis.taxon_latname]
        taxon_latnames = [taxon.taxon_latname for taxon in taxa]

        self.assertEqual(len(expected_taxon_latnames), len(taxon_latnames))

        self.assertEqual(set(expected_taxon_latnames), set(taxon_latnames))

        # TEST HIGHER TAXA
        higher_taxa = generic_form.higher_taxa()
        self.assertEqual(higher_taxa.count(), 1)
        self.assertEqual(higher_taxa[0].name_uuid, quercus.name_uuid)


    @test_settings
    def test_get_field_by_role(self):

        generic_form = self.create_generic_form()
        fields = self.create_all_fields(generic_form)

        taxon_field = generic_form.get_field_by_role('taxonomic_reference')
        self.assertEqual(taxon_field, fields[0])


    @test_settings
    def test_taxonomic_reference_field(self):
        generic_form = self.create_generic_form()
        fields = self.create_all_fields(generic_form)

        taxon_field = generic_form.taxonomic_reference_field()
        
        self.assertEqual(taxon_field, fields[0])
        self.assertEqual(taxon_field.role, 'taxonomic_reference')


    @test_settings
    def test_geographic_reference_field(self):
        generic_form = self.create_generic_form()
        fields = self.create_all_fields(generic_form)

        geo_field = generic_form.geographic_reference_field()
        
        self.assertEqual(geo_field, fields[1])
        self.assertEqual(geo_field.role, 'geographic_reference')


    @test_settings
    def test_temporal_reference_field(self):
        generic_form = self.create_generic_form()
        fields = self.create_all_fields(generic_form)

        time_field = generic_form.temporal_reference_field()
        
        self.assertEqual(time_field, fields[2])
        self.assertEqual(time_field.role, 'temporal_reference')
    

class TestGenericField(WithGenericForm, TenantTestCase):

    def create_all_fields(self, generic_form):

        all_fields = []

        for tup in DJANGO_FIELD_CLASSES:

            field_class = tup[0]
            name = tup[1]


            generic_field = GenericField(
                field_class=field_class,
                render_as=DEFAULT_WIDGETS[field_class],
                role='regular',
                label=str(name),
            )
            generic_field.save(generic_form)

            all_fields.append(generic_field)

        return all_fields


    @test_settings
    def test_save(self):

        generic_form = self.create_generic_form()

        all_fields = self.create_all_fields(generic_form)

        for field in all_fields:
            field.save(generic_form)

        taxon_field = all_fields[0]

        field_link = GenericFieldToGenericForm(
            generic_form=generic_form,
            generic_field=taxon_field,
        )

        field_link.save()


        for role in ['taxonomic_reference', 'geographic_reference', 'temporal_reference']:
            taxon_field.role = role
            taxon_field.save(generic_form)

            field_class = DJANGO_FIELD_CLASSES[0][0]
            
            new_field = GenericField(
                field_class=field_class,
                render_as=DEFAULT_WIDGETS[field_class],
                role=taxon_field.role,
                label=str(field_class),
            )

            with self.assertRaises(ValueError):
                new_field.save(generic_form)
        

    @test_settings
    def test_get_option(self):

        generic_form = self.create_generic_form()

        all_fields = self.create_all_fields(generic_form)

        for field in all_fields:
            self.assertEqual(field.options, None)
            option = field.get_option('doesnotexist')
            self.assertEqual(option, None)

            field.options = {
                'test_option' : 'test_value',
            }

            field.save(generic_form)

            option = field.get_option('test_option')
            self.assertEqual(option, 'test_value')
            

    @test_settings
    def test_value(self):

        generic_form = self.create_generic_form()

        all_fields = self.create_all_fields(generic_form)

        for field in all_fields:

            value = field.value('something')
            self.assertEqual(value, None)

            text_value = 'text_value'
            
            if field.field_class in ['DecimalField', 'FloatField', 'IntegerField']:
                text_value = '5.1'

            generic_value = GenericValues(
                generic_field=field,
                text_value=text_value,
                value_type='choice',
            )
            
            generic_value.save()

            value = field.value('choice')

            if field.field_class in ['DecimalField', 'FloatField']:
                self.assertEqual(value, 5.1)
                
            elif field.field_class == 'IntegerField':
                self.assertEqual(value, 5)

            else:
                self.assertEqual(value, 'text_value')


    @test_settings
    def test_choices(self):

        generic_form = self.create_generic_form()

        all_fields = self.create_all_fields(generic_form)

        for field in all_fields:

            choices = field.choices()

            if field.field_class != 'ChoiceField' and field.field_class != 'MultipleChoiceField':
                self.assertEqual(choices, [])

                choices = ['choice 1', 'choice 2', 'choice 3']
                for choice_value in choices:
                    # add a few choices
                    generic_value = GenericValues(
                        generic_field=field,
                        text_value=choice_value,
                        value_type='choice',
                    )
                    
                    generic_value.save()

                choices = field.choices()
                self.assertEqual(set(choices), set([c.text_value for c in choices]))
                    
            else:
                self.assertEqual(len(choices), 0)


    @test_settings
    def test_str(self):

        generic_form = self.create_generic_form()

        all_fields = self.create_all_fields(generic_form)

        for field in all_fields:

            name = str(field)
            self.assertEqual(name, field.label)


class TestGenericFormVersionBumps(WithGenericForm, TenantTestCase):

    @test_settings
    def test_form_version_bump(self):

        generic_form = self.create_generic_form()

        all_fields = self.create_all_fields(generic_form)

        generic_field = all_fields[0]

        self.assertEqual(generic_form.published_version, None)
        self.assertEqual(generic_form.current_version, 1)

        generic_form.save(set_published_version=True)

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 1)

        generic_field.save(generic_form)
        generic_form.refresh_from_db()

        self.assertEqual(generic_form.published_version, 1)
        self.assertEqual(generic_form.current_version, 2)

        generic_form.save(set_published_version=True)

        self.assertEqual(generic_form.published_version, 2)
        self.assertEqual(generic_form.current_version, 2)

        generic_field.delete()

        generic_form.refresh_from_db()

        self.assertEqual(generic_form.published_version, 2)
        self.assertEqual(generic_form.current_version, 3)

        generic_field_2 = all_fields[1]
        field_link_2 = GenericFieldToGenericForm.objects.get(
            generic_form=generic_form,
            generic_field=generic_field_2,
        )

        generic_form.save(set_published_version=True)
        self.assertEqual(generic_form.published_version, 3)
        self.assertEqual(generic_form.current_version, 3)

        field_link_2.save()
        generic_form.refresh_from_db()
        self.assertEqual(generic_form.published_version, 3)
        self.assertEqual(generic_form.current_version, 4)

        generic_form.save(set_published_version=True)
        field_link_2.refresh_from_db()
        self.assertEqual(generic_form.published_version, 4)
        self.assertEqual(generic_form.current_version, 4)

        field_link_2.delete()
        generic_form.refresh_from_db()
        self.assertEqual(generic_form.published_version, 4)
        self.assertEqual(generic_form.current_version, 5)


        choice_field_link = GenericFieldToGenericForm.objects.get(generic_form=generic_form,
            generic_field__field_class='ChoiceField')

        choice_field = choice_field_link.generic_field

        values = GenericValues.objects.filter(generic_field=choice_field)

        value_1 = values[0]

        generic_form.save(set_published_version=True)
        self.assertEqual(generic_form.published_version, 5)
        self.assertEqual(generic_form.current_version, 5)

        value_1.save()

        generic_form.refresh_from_db()
        self.assertEqual(generic_form.published_version, 5)
        self.assertEqual(generic_form.current_version, 6)

        generic_form.save(set_published_version=True)
        self.assertEqual(generic_form.published_version, 6)
        self.assertEqual(generic_form.current_version, 6)

        value_1.delete()

        generic_form.refresh_from_db()
        self.assertEqual(generic_form.published_version, 6)
        self.assertEqual(generic_form.current_version, 7)


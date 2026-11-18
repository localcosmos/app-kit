import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxon_profiles', '0017_taxonprofile_featured_from_and_more'),
        ('object_classes', '0002_objectclass_category'),
    ]

    operations = [
        # Remove old constraints that reference the CharField 'morphotype'
        migrations.RemoveConstraint(
            model_name='taxonprofile',
            name='tp_unique_taxon_morphotype_objectclass',
        ),
        migrations.RemoveConstraint(
            model_name='taxonprofile',
            name='tp_unique_taxon_morphotype_no_objectclass',
        ),
        migrations.RemoveConstraint(
            model_name='taxonprofile',
            name='tp_unique_taxon_objectclass_no_morphotype',
        ),
        migrations.RemoveConstraint(
            model_name='taxonprofile',
            name='tp_unique_taxon_no_morphotype_no_objectclass',
        ),
        # Rename the CharField to legacy_morphotype
        migrations.RenameField(
            model_name='taxonprofile',
            old_name='morphotype',
            new_name='legacy_morphotype',
        ),
        migrations.AlterField(
            model_name='taxonprofile',
            name='legacy_morphotype',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        # Add the new FK morphotype → ObjectClass(category='morphotype')
        migrations.AddField(
            model_name='taxonprofile',
            name='morphotype',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='taxon_profiles',
                limit_choices_to={'category': 'morphotype'},
                to='object_classes.objectclass',
            ),
        ),
        # Add new constraints referencing morphotype
        migrations.AddConstraint(
            model_name='taxonprofile',
            constraint=models.UniqueConstraint(
                condition=models.Q(morphotype__isnull=False, object_class__isnull=False),
                fields=['taxon_profiles', 'taxon_source', 'name_uuid', 'morphotype', 'object_class'],
                name='tp_unique_taxon_morphotype_objectclass',
            ),
        ),
        migrations.AddConstraint(
            model_name='taxonprofile',
            constraint=models.UniqueConstraint(
                condition=models.Q(morphotype__isnull=False, object_class__isnull=True),
                fields=['taxon_profiles', 'taxon_source', 'name_uuid', 'morphotype'],
                name='tp_unique_taxon_morphotype_no_objectclass',
            ),
        ),
        migrations.AddConstraint(
            model_name='taxonprofile',
            constraint=models.UniqueConstraint(
                condition=models.Q(morphotype__isnull=True, object_class__isnull=False),
                fields=['taxon_profiles', 'taxon_source', 'name_uuid', 'object_class'],
                name='tp_unique_taxon_objectclass_no_morphotype',
            ),
        ),
       migrations.AddConstraint(
            model_name='taxonprofile',
            constraint=models.UniqueConstraint(
                condition=models.Q(morphotype__isnull=True, object_class__isnull=True, legacy_morphotype__isnull=True),
                fields=['taxon_profiles', 'taxon_source', 'name_uuid'],
                name='tp_unique_taxon_no_morphotype_no_objectclass',
            ),
        ),
        # Preserve legacy-morphotype uniqueness until rows are migrated to FK morphotype.
        migrations.AddConstraint(
            model_name='taxonprofile',
            constraint=models.UniqueConstraint(
                condition=models.Q(morphotype__isnull=True, object_class__isnull=False, legacy_morphotype__isnull=False),
                fields=['taxon_profiles', 'taxon_source', 'name_uuid', 'legacy_morphotype', 'object_class'],
                name='tp_unique_taxon_legacy_morphotype_objectclass',
            ),
        ),
        migrations.AddConstraint(
            model_name='taxonprofile',
            constraint=models.UniqueConstraint(
                condition=models.Q(morphotype__isnull=True, object_class__isnull=True, legacy_morphotype__isnull=False),
                fields=['taxon_profiles', 'taxon_source', 'name_uuid', 'legacy_morphotype'],
                name='tp_unique_taxon_legacy_morphotype_no_objectclass',
            ),
        ),
    ]

# Generated by Django 4.1.5 on 2023-12-13 14:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('taxon_profiles', '0006_taxonprofile_publication_status'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='taxonprofile',
            unique_together={('taxon_profiles', 'taxon_source', 'name_uuid')},
        ),
    ]

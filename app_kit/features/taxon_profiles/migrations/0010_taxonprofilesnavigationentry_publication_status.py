# Generated by Django 5.1.7 on 2025-03-24 09:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxon_profiles', '0009_taxonprofile_is_featured'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxonprofilesnavigationentry',
            name='publication_status',
            field=models.CharField(choices=[('draft', 'draft'), ('publish', 'publish')], default='publish', max_length=100),
        ),
    ]

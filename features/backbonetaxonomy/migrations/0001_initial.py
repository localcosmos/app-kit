# Generated by Django 3.1 on 2020-08-27 12:25

import app_kit.generic
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BackboneTaxonomy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('primary_language', models.CharField(max_length=15)),
                ('name', models.CharField(max_length=255, null=True)),
                ('published_version', models.IntegerField(null=True)),
                ('current_version', models.IntegerField(default=1)),
                ('is_locked', models.BooleanField(default=False)),
                ('messages', models.JSONField(null=True)),
                ('global_options', models.JSONField(null=True)),
            ],
            options={
                'verbose_name': 'Backbone taxonomy',
                'verbose_name_plural': 'Backbone taxonomies',
            },
            bases=(app_kit.generic.GenericContentMethodsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='BackboneTaxa',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('taxon_latname', models.CharField(max_length=255)),
                ('taxon_author', models.CharField(max_length=255, null=True)),
                ('taxon_source', models.CharField(max_length=255)),
                ('taxon_include_descendants', models.BooleanField(default=False)),
                ('taxon_nuid', models.CharField(max_length=255)),
                ('name_uuid', models.UUIDField()),
                ('backbonetaxonomy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backbonetaxonomy.backbonetaxonomy')),
            ],
            options={
                'verbose_name': 'Backbone taxonomy',
                'verbose_name_plural': 'Backbone taxonomies',
                'unique_together': {('backbonetaxonomy', 'taxon_latname', 'taxon_author')},
            },
        ),
    ]

# Generated by Django 3.1 on 2020-08-27 12:25

import app_kit.generic
import app_kit.models
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TaxonProfiles',
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
                'verbose_name': 'Taxon profiles',
                'verbose_name_plural': 'Taxon profiles',
            },
            bases=(app_kit.generic.GenericContentMethodsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='TaxonTextType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text_type', models.CharField(max_length=255)),
                ('position', models.IntegerField(default=0)),
                ('taxon_profiles', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='taxon_profiles.taxonprofiles')),
            ],
            options={
                'unique_together': {('taxon_profiles', 'text_type')},
            },
        ),
        migrations.CreateModel(
            name='TaxonProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('taxon_latname', models.CharField(max_length=255)),
                ('taxon_author', models.CharField(max_length=255, null=True)),
                ('taxon_source', models.CharField(max_length=255)),
                ('taxon_include_descendants', models.BooleanField(default=False)),
                ('taxon_nuid', models.CharField(max_length=255)),
                ('name_uuid', models.UUIDField()),
                ('taxon_profiles', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='taxon_profiles.taxonprofiles')),
            ],
            options={
                'unique_together': {('taxon_source', 'taxon_latname', 'taxon_author')},
            },
            bases=(app_kit.models.ContentImageMixin, models.Model),
        ),
        migrations.CreateModel(
            name='TaxonText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('position', models.IntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('taxon_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='taxon_profiles.taxonprofile')),
                ('taxon_text_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='taxon_profiles.taxontexttype')),
            ],
            options={
                'unique_together': {('taxon_profile', 'taxon_text_type')},
            },
        ),
    ]

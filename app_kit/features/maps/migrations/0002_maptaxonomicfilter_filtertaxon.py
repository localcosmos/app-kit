# Generated by Django 4.1.5 on 2023-05-17 08:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MapTaxonomicFilter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=355)),
                ('position', models.IntegerField(default=0)),
                ('map', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='maps.map')),
            ],
            options={
                'ordering': ('position',),
            },
        ),
        migrations.CreateModel(
            name='FilterTaxon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('taxon_latname', models.CharField(max_length=255)),
                ('taxon_author', models.CharField(max_length=255, null=True)),
                ('taxon_source', models.CharField(max_length=255)),
                ('taxon_include_descendants', models.BooleanField(default=False)),
                ('taxon_nuid', models.CharField(max_length=255)),
                ('name_uuid', models.UUIDField()),
                ('taxonomic_filter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='maps.maptaxonomicfilter')),
            ],
            options={
                'unique_together': {('taxonomic_filter', 'name_uuid')},
            },
        ),
    ]

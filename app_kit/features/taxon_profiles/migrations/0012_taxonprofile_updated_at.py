# Generated by Django 5.1.7 on 2025-04-02 13:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxon_profiles', '0011_alter_taxontexttype_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxonprofile',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]

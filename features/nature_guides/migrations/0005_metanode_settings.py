# Generated by Django 3.1.12 on 2022-02-23 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nature_guides', '0004_auto_20210616_1315'),
    ]

    operations = [
        migrations.AddField(
            model_name='metanode',
            name='settings',
            field=models.JSONField(null=True),
        ),
    ]

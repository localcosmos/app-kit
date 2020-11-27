# Generated by Django 3.1 on 2020-11-20 09:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fact_sheets', '0002_factsheet_created_by'),
    ]

    operations = [
        migrations.RenameField(
            model_name='factsheet',
            old_name='content',
            new_name='contents',
        ),
        migrations.AlterField(
            model_name='factsheet',
            name='title',
            field=models.CharField(default='title', max_length=355),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='factsheetimages',
            name='content',
            field=models.CharField(default='image', max_length=355),
            preserve_default=False,
        ),
    ]
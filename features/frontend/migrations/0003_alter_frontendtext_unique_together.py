# Generated by Django 4.1.5 on 2023-09-13 20:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0002_frontend_configuration'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='frontendtext',
            unique_together={('frontend', 'identifier', 'frontend_name')},
        ),
    ]

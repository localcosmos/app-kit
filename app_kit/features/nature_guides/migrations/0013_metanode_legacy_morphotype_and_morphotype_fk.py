import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nature_guides', '0012_object_classes_and_more'),
        ('object_classes', '0002_objectclass_category'),
    ]

    operations = [
        migrations.RenameField(
            model_name='metanode',
            old_name='morphotype',
            new_name='legacy_morphotype',
        ),
        migrations.AlterField(
            model_name='metanode',
            name='legacy_morphotype',
            field=models.CharField(blank=True, max_length=355, null=True),
        ),
        migrations.AddField(
            model_name='metanode',
            name='morphotype',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='meta_nodes',
                limit_choices_to={'category': 'morphotype'},
                to='object_classes.objectclass',
            ),
        ),
    ]

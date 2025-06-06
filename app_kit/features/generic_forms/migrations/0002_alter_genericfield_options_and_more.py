# Generated by Django 5.1.7 on 2025-04-28 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generic_forms', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='genericfield',
            options={'verbose_name': 'Observation Form Field', 'verbose_name_plural': 'Observation Form Fields'},
        ),
        migrations.AlterField(
            model_name='genericfield',
            name='field_class',
            field=models.CharField(choices=[('BooleanField', 'Checkbox field'), ('CharField', 'Text field'), ('ChoiceField', 'Choice field'), ('DecimalField', 'Decimal number field (fixed precision)'), ('FloatField', 'Floating number field (precision not fixed)'), ('IntegerField', 'Integer field'), ('MultipleChoiceField', 'Multiple choice field'), ('DateTimeJSONField', 'Datetime field'), ('TaxonField', 'Taxon field'), ('SelectTaxonField', 'Select taxon field'), ('PointJSONField', 'Point field'), ('PictureField', 'Image field')], max_length=255),
        ),
        migrations.AlterField(
            model_name='genericfield',
            name='render_as',
            field=models.CharField(choices=[('CheckboxInput', 'Checkbox'), ('TextInput', 'Single line text input'), ('Textarea', 'Multi-line text input'), ('NumberInput', 'Number field'), ('MobileNumberInput', 'Number input with +/- buttons'), ('HiddenInput', 'Hidden field'), ('Select', 'Dropdown'), ('CheckboxSelectMultiple', 'Multiple choice'), ('RadioSelect', 'Radio'), ('SelectDateTimeWidget', 'Date and time with autofill'), ('MobilePositionInput', 'GPS-supported point input with map'), ('PointOrAreaInput', 'GPS-supported point or area input with map'), ('BackboneTaxonAutocompleteWidget', 'Taxon input with backend search'), ('CameraAndAlbumWidget', 'Camera and album'), ('FixedTaxonWidget', 'Fixed taxon'), ('SelectTaxonWidget', 'Select taxon widget')], max_length=255),
        ),
    ]

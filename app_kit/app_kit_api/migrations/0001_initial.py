# Generated by Django 3.1 on 2020-08-27 12:24

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppKitStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('live', 'live'), ('maintenance', 'maintenance')], default='live', max_length=50)),
                ('site', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='sites.site')),
            ],
        ),
        migrations.CreateModel(
            name='AppKitJobs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('meta_app_uuid', models.UUIDField()),
                ('meta_app_definition', models.JSONField()),
                ('app_version', models.IntegerField()),
                ('platform', models.CharField(choices=[('ios', 'iOS'), ('android', 'Android')], max_length=255)),
                ('job_type', models.CharField(choices=[('build', 'Build'), ('release', 'Release')], max_length=50)),
                ('parameters', models.JSONField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('assigned_to', models.CharField(max_length=100, null=True)),
                ('assigned_at', models.DateTimeField(null=True)),
                ('finished_at', models.DateTimeField(null=True)),
                ('job_status', models.CharField(choices=[('waiting_for_assignment', 'Waiting for assignment'), ('assigned', 'Assigned'), ('in_progress', 'Job in progress'), ('success', 'Success'), ('failed', 'Failed')], default='waiting_for_assignment', max_length=50)),
                ('job_result', models.JSONField(null=True)),
            ],
            options={
                'unique_together': {('meta_app_uuid', 'app_version', 'platform', 'job_type')},
            },
        ),
    ]
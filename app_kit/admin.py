from django.contrib import admin

from .models import MetaApp

class MetaAppAdmin(admin.ModelAdmin):
    fields = ('is_locked', 'build_status', 'validation_status', 'package_name')

admin.site.register(MetaApp, MetaAppAdmin)

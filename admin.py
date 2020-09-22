from django.contrib import admin

from .models import MetaApp

class MetaAppAdmin(admin.ModelAdmin):
    pass

admin.site.register(MetaApp, MetaAppAdmin)

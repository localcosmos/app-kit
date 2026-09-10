from django.contrib import admin

from .models import MetaApp

from app_kit.features.frontend.models import Frontend

class MetaAppAdmin(admin.ModelAdmin):
    fields = ('is_locked', 'build_status', 'validation_status', 'package_name')

admin.site.register(MetaApp, MetaAppAdmin)


class FrontendAdmin(admin.ModelAdmin):
    fields = ('is_locked',)

admin.site.register(Frontend, FrontendAdmin)
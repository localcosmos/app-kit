from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from .models import MetaApp

@admin.register(MetaApp)
class MetaAppAdmin(TenantAdminMixin, admin.ModelAdmin):
    pass

from django.contrib import admin

from .models import TenantUserRole

class TenantUserRoleAdmin(admin.ModelAdmin):
    pass

admin.site.register(TenantUserRole, TenantUserRoleAdmin)

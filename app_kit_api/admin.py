from django.contrib import admin

from .models import AppKitStatus

class AppKitStatusAdmin(admin.ModelAdmin):
    pass

admin.site.register(AppKitStatus, AppKitStatusAdmin)

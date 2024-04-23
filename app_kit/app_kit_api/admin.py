from django.contrib import admin

from .models import AppKitStatus, AppKitJobs

class AppKitStatusAdmin(admin.ModelAdmin):
    pass

admin.site.register(AppKitStatus, AppKitStatusAdmin)


class AppKitJobsAdmin(admin.ModelAdmin):
    pass

admin.site.register(AppKitJobs, AppKitJobsAdmin)
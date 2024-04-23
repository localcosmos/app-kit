from django.conf import settings

def app_kit_context(request):
    context =  {
        'app_kit_mode' : settings.APP_KIT_MODE,
        'app_kit_sandbox_user' : settings.APP_KIT_SANDBOX_USER,
        'app_kit_sandbox_password' : settings.APP_KIT_SANDBOX_PASSWORD,
        'app_kit_short_name' : getattr(settings, 'APP_KIT_SHORT_NAME', 'LC APP KIT'),
        'app_kit_long_name' : getattr(settings, 'APP_KIT_LONG_NAME', 'LOCAL COSMOS APP KIT'),
    }

    return context

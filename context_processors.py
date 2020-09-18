from django.conf import settings

def app_kit_mode(request):
    context =  {
        'app_kit_mode' : settings.APP_KIT_MODE,
        'app_kit_sandbox_user' : settings.APP_KIT_SANDBOX_USER,
        'app_kit_sandbox_password' : settings.APP_KIT_SANDBOX_PASSWORD,
    }

    return context

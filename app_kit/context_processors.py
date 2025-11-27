from django.conf import settings
import importlib.metadata

def app_kit_context(request):
    try:
        app_kit_version = importlib.metadata.version('localcosmos_app_kit')
    except importlib.metadata.PackageNotFoundError:
        app_kit_version = 'unknown'
    
    context = {
        'app_kit_mode': settings.APP_KIT_MODE,
        'app_kit_sandbox_user': settings.APP_KIT_SANDBOX_USER,
        'app_kit_sandbox_password': settings.APP_KIT_SANDBOX_PASSWORD,
        'app_kit_short_name': getattr(settings, 'APP_KIT_SHORT_NAME', 'LC APP KIT'),
        'app_kit_long_name': getattr(settings, 'APP_KIT_LONG_NAME', 'LOCAL COSMOS APP KIT'),
        'app_kit_version': app_kit_version,
    }

    return context

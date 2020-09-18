from django.urls import path, include
from . import setup_views


urlpatterns = [
    # SETUP
    path('setup/initial-appkit/', setup_views.SetupInitialAppKit.as_view(), name='setup_initial_appkit'),
    path('setup/check-initial-appkit-creation/<str:schema_name>/',
         setup_views.CheckInitialAppKitCreationStatus.as_view(),
         name='setup_check_initial_appkit_creation'),
]

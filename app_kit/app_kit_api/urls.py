from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

app_name = 'build_api'

urlpatterns = [
    # app unspecific
    path('', views.APIHome.as_view(), name='appkit_api_home'),
    path('auth-token/', views.ObtainLCAuthToken.as_view(), name='get_appkit_api_token'),
    path('jobs/', views.AppKitJobList.as_view(), name='job_list'),
    path('jobs/<int:pk>/', views.AppKitJobDetail.as_view(), name='job_detail'),
    path('jobs/<int:pk>/assign/', views.AssignAppKitJob.as_view(), name='assign_job'),
    path('jobs/<int:pk>/status/', views.UpdateAppKitJobStatus.as_view(), name='update_job_status'),
    path('jobs/<int:pk>/completed/', views.CompletedAppKitJob.as_view(), name='completed_job'),
    path('create-appkit/', views.CreateAppKit.as_view(), name='api_create_appkit'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json',])

from django.urls import include, path

from django.contrib.auth import views as auth_views
from localcosmos_server import views as localcosmos_server_views

from . import views

urlpatterns = [
    # essentials - use a different base template than localcosmos_server does
    # pass "next" kwarg to LoginView
    path('log-in/', localcosmos_server_views.LogIn.as_view(
        extra_context={'base_template': 'app_kit/base.html', 'next':'/app-kit'}), name='log_in'),
    
    path('log-out/', auth_views.LogoutView.as_view(extra_context={'base_template': 'app_kit/base.html'}),
         name='log_out'),
    path('loggedout/', localcosmos_server_views.LoggedOut.as_view(
        extra_context={'base_template': 'app_kit/base.html'}), name='loggedout'),

    path('password-change/', auth_views.PasswordChangeView.as_view(
        extra_context={'base_template': 'app_kit/base.html'},
        template_name='localcosmos_server/registration/password_change_form.html'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        extra_context={'base_template': 'app_kit/base.html'},
        template_name='localcosmos_server/registration/password_change_done.html'), name='password_change_done'),
    
    path('password-reset/', views.TenantPasswordResetView.as_view(
        extra_context={'base_template': 'app_kit/base.html'},
        template_name='localcosmos_server/registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        extra_context={'base_template': 'app_kit/base.html'},
        template_name='localcosmos_server/registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        extra_context={'base_template': 'app_kit/base.html'},
        template_name='localcosmos_server/registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        extra_context={'base_template': 'app_kit/base.html'},
        template_name='localcosmos_server/registration/password_reset_complete.html'), name='password_reset_complete'),
    # LEGAL
    path('privacy-statement/', views.PrivacyStatement.as_view(), name='privacy_statement'),
    path('legal-notice/', views.LegalNotice.as_view(), name='legal_notice'),
]

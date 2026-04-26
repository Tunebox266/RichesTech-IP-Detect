"""
Main URL configuration for MELTSA-TaTU.
"""
# config/urls.py (final version)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

# API Documentation
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    

    # App URLs
    # Core app
    path('', include(('apps.core.urls', 'core'), namespace='core')),
    path('core/', include(('apps.core.urls', 'core'), namespace='core')),
    
    #path('accounts/', include('apps.accounts.urls')),
    # Accounts app
    path('accounts/', include(('apps.accounts.urls', 'accounts'), namespace='accounts')),
    path('courses/', include('apps.courses.urls')),
    path('payments/', include('apps.payments.urls')),
    path('events/', include('apps.events.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('messaging/', include('apps.messaging.urls')),
    path('complaints/', include('apps.complaints.urls')),
    path('directory/', include('apps.directory.urls')),
    
    # Password reset URLs (built-in)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
         
    # API endpoints
    path('api/', include('apps.api.urls')),
    
]

# Debug toolbar
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        path('media/<path:path>', RedirectView.as_view(url=settings.MEDIA_URL + '%(path)s')),
    ]

# Custom error handlers
handler404 = 'apps.core.views.handler404'
handler500 = 'apps.core.views.handler500'
handler403 = 'apps.core.views.handler403'
handler400 = 'apps.core.views.handler400'

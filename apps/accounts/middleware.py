# accounts/middleware.py
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import redirect
from django.contrib import messages
from .models import ActivityLog, LoginAttempt
import datetime

class LoginRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path == '/login/' and request.method == 'POST':
            ip = self.get_client_ip(request)
            key = f'login_attempts_{ip}'
            attempts = cache.get(key, 0)
            
            if attempts >= 5:
                messages.error(request, 'Too many login attempts. Try again in 15 minutes.')
                return redirect('login')
            
            cache.set(key, attempts + 1, timeout=900)  # 15 minutes
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            # Log login actions
            if request.path == '/login/' and request.method == 'POST' and response.status_code == 302:
                ActivityLog.objects.create(
                    user=request.user,
                    action_type='login',
                    ip_address=self.get_client_ip(request),
                    details={'user_agent': request.META.get('HTTP_USER_AGENT', '')}
                )
            
            # Log logout
            elif request.path == '/logout/':
                ActivityLog.objects.create(
                    user=request.user,
                    action_type='logout',
                    ip_address=self.get_client_ip(request),
                    details={}
                )
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
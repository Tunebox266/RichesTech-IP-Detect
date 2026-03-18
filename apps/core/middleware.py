# apps/core/middleware.py

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

class PasscodeProtectionMiddleware:
    """
    Middleware to ensure users go through passcode before accessing login page
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Define the login URL patterns to protect
        login_paths = ['/accounts/login/', '/accounts/login', '/accounts/login/']
        
        # Check if the requested path is the login page
        if request.path in login_paths:
            # Check if user is already authenticated (skip passcode)
            if request.user.is_authenticated:
                return self.get_response(request)
            
            # Check if passcode has been verified in this session
            passcode_verified = request.session.get('passcode_verified', False)
            verified_time = request.session.get('passcode_verified_time')
            
            # If passcode verified within last 10 minutes, allow access
            if passcode_verified and verified_time:
                try:
                    # Parse the stored time
                    if isinstance(verified_time, str):
                        from django.utils.dateparse import parse_datetime
                        verified_datetime = parse_datetime(verified_time)
                    else:
                        verified_datetime = verified_time
                    
                    # Check if within 10 minutes
                    if verified_datetime and (timezone.now() - verified_datetime) < timedelta(minutes=10):
                        # Allow access to login page - DON'T clear the session flags yet
                        # They will be cleared after successful login
                        return self.get_response(request)
                except Exception as e:
                    print(f"Passcode verification error: {e}")
                    # If any error, clear the flags
                    if 'passcode_verified' in request.session:
                        del request.session['passcode_verified']
                    if 'passcode_verified_time' in request.session:
                        del request.session['passcode_verified_time']
            
            # If not verified, redirect to home with passcode modal trigger
            response = redirect('/?require_passcode=true')
            return response
        
        # Clear passcode verification if user logs out
        if request.path == '/accounts/logout/':
            if 'passcode_verified' in request.session:
                del request.session['passcode_verified']
            if 'passcode_verified_time' in request.session:
                del request.session['passcode_verified_time']
        
        return self.get_response(request)
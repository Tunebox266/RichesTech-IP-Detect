# apps/core/decorators.py

from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from functools import wraps

def passcode_required(view_func):
    """
    Decorator to ensure passcode verification before accessing a view
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Skip for authenticated users
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        # Check if passcode verified in session
        passcode_verified = request.session.get('passcode_verified', False)
        verified_time = request.session.get('passcode_verified_time')
        
        if passcode_verified and verified_time:
            try:
                from django.utils.dateparse import parse_datetime
                if isinstance(verified_time, str):
                    verified_datetime = parse_datetime(verified_time)
                else:
                    verified_datetime = verified_time
                
                if verified_datetime and (timezone.now() - verified_datetime) < timedelta(minutes=10):
                    return view_func(request, *args, **kwargs)
            except:
                pass
        
        # If not verified, redirect to home with passcode requirement
        return redirect('/?require_passcode=true')
    
    return _wrapped_view
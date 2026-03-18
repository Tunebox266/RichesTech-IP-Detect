# core/context_processors.py
from django.db.models import Q
from django.conf import settings
from .models import Notification, AcademicSetting
from apps.messaging.models import Message

def site_settings(request):
    """Global context variables"""
    context = {
        'academic_year': AcademicSetting.objects.filter(is_active=True).first(),
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY if hasattr(settings, 'PAYSTACK_PUBLIC_KEY') else None,
    }
    
    # Add notification count for authenticated users
    if request.user.is_authenticated:
        context['unread_notifications'] = Notification.objects.filter(
            Q(is_global=True) | Q(target_users=request.user)
        ).exclude(read_by=request.user).count()
        
        context['unread_messages'] = Message.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
    
    return context
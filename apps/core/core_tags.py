# core/templatetags/core_tags.py
from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def days_until(date):
    """Return days until given date"""
    if not date:
        return 0
    delta = date - timezone.now().date()
    return delta.days

@register.filter
def has_paid(user, due):
    """Check if user has paid a specific due"""
    from payments.models import Payment
    return Payment.objects.filter(
        student=user,
        due=due,
        status='success'
    ).exists()

@register.filter
def event_color(event_type):
    """Return Bootstrap color class for event type"""
    color_map = {
        'academic': 'primary',
        'registration': 'success',
        'examination': 'warning',
        'holiday': 'danger',
        'event': 'info',
        'deadline': 'secondary',
    }
    return color_map.get(event_type, 'secondary')

@register.simple_tag
def get_notifications(user, limit=5):
    """Get notifications for user"""
    from core.models import Notification
    return Notification.objects.filter(
        Q(is_global=True) | Q(target_users=user)
    ).exclude(read_by=user)[:limit]

@register.filter
def message_preview(text, length=50):
    """Create message preview"""
    if len(text) <= length:
        return text
    return text[:length] + '...'

@register.filter
def time_ago(date):
    """Return human-readable time difference"""
    now = timezone.now()
    diff = now - date
    
    if diff < timedelta(minutes=1):
        return 'just now'
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    elif diff < timedelta(days=7):
        days = diff.days
        return f'{days} day{"s" if days != 1 else ""} ago'
    else:
        return date.strftime('%b %d, %Y')
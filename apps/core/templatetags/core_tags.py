# core/templatetags/core_tags.py
from django import template
from django.utils import timezone
from datetime import timedelta
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


register = template.Library()

# apps/core/templatetags/core_tags.py

@register.filter
def split(value, arg):
    """Split a string by the given argument and return the parts"""
    if not value:
        return []
    return value.split(arg)



@register.filter
def meeting_status_color(status):
    """Return Bootstrap color class for meeting status"""
    color_map = {
        'scheduled': 'primary',
        'ongoing': 'success',
        'completed': 'secondary',
        'cancelled': 'danger',
    }
    return color_map.get(status, 'secondary')

@register.filter
def user_type_badge(user_type):
    """Return badge class for user type"""
    badge_map = {
        'admin': 'danger',
        'staff': 'warning',
        'executive': 'info',
        'student': 'success',
    }
    return badge_map.get(user_type, 'secondary')

@register.filter
def program_type_badge(program):
    """Return badge class for program type"""
    badge_map = {
        'regular': 'success',
        'weekend': 'warning',
    }
    return badge_map.get(program, 'secondary')

@register.simple_tag
def get_user_avatar(user, size=40):
    """Get user avatar URL or default"""
    if user.profile_image:
        return user.profile_image.url
    return f'https://ui-avatars.com/api/?name={user.get_full_name()}&size={size}&background=random'

@register.filter
def time_until(dt):
    """Return time until given datetime"""
    if not dt:
        return ''
    
    now = timezone.now()
    if dt < now:
        return 'Started'
    
    diff = dt - now
    
    if diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f'in {minutes} minutes'
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f'in {hours} hours'
    else:
        days = diff.days
        return f'in {days} days'


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
def youtube_embed(url):
    """Convert YouTube URL to embed URL"""
    if not url:
        return ''
    
    video_id = extract_youtube_id(url)
    if video_id:
        return f'https://www.youtube.com/embed/{video_id}'
    return url


@register.filter
def vimeo_embed(url):
    """Convert Vimeo URL to embed URL"""
    if not url:
        return ''
    
    video_id = extract_vimeo_id(url)
    if video_id:
        return f'https://player.vimeo.com/video/{video_id}'
    return url


@register.filter
def is_youtube_url(url):
    """Check if URL is a YouTube URL"""
    if not url:
        return False
    return extract_youtube_id(url) is not None


@register.filter
def is_vimeo_url(url):
    """Check if URL is a Vimeo URL"""
    if not url:
        return False
    return extract_vimeo_id(url) is not None


def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    if not url:
        return None
    
    # Clean the URL first (remove tracking parameters)
    url = url.split('?')[0] if '?' in url else url
    
    # YouTube URL patterns
    patterns = [
        r'youtube\.com/watch\?v=([^&]+)',
        r'youtu\.be/([^?]+)',
        r'youtube\.com/embed/([^?]+)',
        r'youtube\.com/v/([^?]+)',
        r'youtube\.com/shorts/([^?]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Try parsing with urlparse for complex cases
    try:
        parsed_url = urlparse(url)
        if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
            if parsed_url.path == '/watch':
                query_params = parse_qs(parsed_url.query)
                if 'v' in query_params:
                    return query_params['v'][0]
            elif parsed_url.path.startswith('/embed/') or parsed_url.path.startswith('/v/'):
                return parsed_url.path.split('/')[-1]
            elif 'youtu.be' in parsed_url.netloc:
                return parsed_url.path.strip('/')
    except:
        pass
    
    return None


def extract_vimeo_id(url):
    """Extract Vimeo video ID from URL"""
    if not url:
        return None
    
    # Clean the URL first (remove tracking parameters)
    url = url.split('?')[0] if '?' in url else url
    
    # Vimeo URL patterns
    patterns = [
        r'vimeo\.com/(\d+)',
        r'vimeo\.com/channels/[^/]+/(\d+)',
        r'vimeo\.com/groups/[^/]+/videos/(\d+)',
        r'player\.vimeo\.com/video/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


@register.filter
def get_youtube_id(url):
    """Get YouTube video ID (for thumbnail generation)"""
    return extract_youtube_id(url) or ''


@register.filter
def get_vimeo_id(url):
    """Get Vimeo video ID"""
    return extract_vimeo_id(url) or ''


@register.filter
def youtube_thumbnail(url):
    """Get YouTube thumbnail URL"""
    video_id = extract_youtube_id(url)
    if video_id:
        return f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
    return ''


@register.filter
def clean_url(url):
    """Remove tracking parameters from URL"""
    if not url:
        return url
    
    # Split URL and remove query parameters
    return url.split('?')[0]
    
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

@register.filter
def notification_color(notification_type):

    colors = {
        "info": "primary",
        "success": "success",
        "warning": "warning",
        "error": "danger",
        "message": "info",
        "announcement": "primary",
        "payment": "success",
        "event": "warning",
    }

    return colors.get(notification_type, "secondary")


@register.filter
def notification_icon(notification_type):

    icons = {
        "info": "info-circle",
        "success": "check-circle",
        "warning": "exclamation-triangle",
        "error": "times-circle",
        "message": "envelope",
        "announcement": "bullhorn",
        "payment": "credit-card",
        "event": "calendar",
    }

    return icons.get(notification_type, "bell")



# Activity color filter
@register.filter
def activity_color(activity_type):

    colors = {
        "login": "success",
        "logout": "secondary",
        "update": "info",
        "delete": "danger",
        "create": "primary",
    }

    return colors.get(activity_type, "secondary")


# Complaint status color
@register.filter
def complaint_status_color(status):

    colors = {
        "pending": "warning",
        "in_progress": "info",
        "resolved": "success",
        "rejected": "danger",
    }

    return colors.get(status, "secondary")


# Notification color
@register.filter
def notification_color(notification_type):

    colors = {
        "info": "primary",
        "success": "success",
        "warning": "warning",
        "error": "danger",
        "message": "info",
    }

    return colors.get(notification_type, "secondary")


# 🔹 NEW FILTER: notification_icon
@register.filter
def notification_icon(notification_type):
    """
    Returns a FontAwesome icon class for the notification type.
    """
    icons = {
        "info": "fa-info-circle",
        "success": "fa-check-circle",
        "warning": "fa-exclamation-triangle",
        "error": "fa-times-circle",
        "message": "fa-envelope",
    }
    return icons.get(notification_type, "fa-bell")


# 🔹 NEW FILTER: activity_icon
@register.filter
def activity_icon(activity_type):
    """
    Returns a FontAwesome icon class for a user activity type.
    Example activity types: login, logout, update, delete, create
    """
    icons = {
        "login": "fa-sign-in-alt",
        "logout": "fa-sign-out-alt",
        "update": "fa-edit",
        "delete": "fa-trash",
        "create": "fa-plus-circle",
        "password_change": "fa-key",
    }
    return icons.get(activity_type, "fa-info-circle")


@register.filter
def priority_color(priority):
    """
    Returns Bootstrap color class for announcement priority
    """
    colors = {
        "low": "secondary",
        "normal": "primary",
        "medium": "info",
        "high": "warning",
        "urgent": "danger",
    }
    return colors.get(str(priority).lower(), "secondary")

@register.filter
def material_color(material_type):
    """
    Returns Bootstrap color class for course materials
    """
    colors = {
        "pdf": "danger",
        "document": "primary",
        "doc": "primary",
        "ppt": "warning",
        "presentation": "warning",
        "video": "success",
        "audio": "info",
        "image": "secondary",
        "link": "dark",
    }

    return colors.get(str(material_type).lower(), "secondary")

@register.filter
def material_icon(material_type):
    """
    Returns FontAwesome icon for material types
    """
    icons = {
        "pdf": "file-pdf",
        "document": "file-word",
        "doc": "file-word",
        "ppt": "file-powerpoint",
        "presentation": "file-powerpoint",
        "video": "video",
        "audio": "music",
        "image": "image",
        "link": "link",
    }

    return icons.get(str(material_type).lower(), "file")

@register.filter
def event_color(event_type):
    """
    Returns a Bootstrap color for event types
    """
    colors = {
        "meeting": "primary",
        "workshop": "success",
        "seminar": "info",
        "training": "warning",
        "conference": "secondary",
        "social": "danger",
    }

    return colors.get(str(event_type).lower(), "primary")

@register.filter
def event_icon(event_type):
    icons = {
        "meeting": "users",
        "workshop": "tools",
        "seminar": "chalkboard-teacher",
        "training": "graduation-cap",
        "conference": "microphone",
        "social": "glass-cheers",
    }

    return icons.get(str(event_type).lower(), "calendar")

# Complaint type color
@register.filter
def complaint_color(value):

    colors = {
        "academic": "primary",
        "administration": "warning",
        "facility": "danger",
        "other": "secondary",
    }

    return colors.get(value, "secondary")


# Complaint status color
@register.filter
def status_color(value):

    colors = {
        "pending": "warning",
        "in_progress": "info",
        "resolved": "success",
        "rejected": "danger",
    }

    return colors.get(value, "secondary")


# Task priority color
@register.filter
def task_priority_color(value):

    colors = {
        "low": "success",
        "medium": "warning",
        "high": "danger",
        "urgent": "dark",
    }

    return colors.get(value, "secondary")


# Task status color
@register.filter
def task_status_color(value):

    colors = {
        "pending": "warning",
        "in_progress": "info",
        "completed": "success",
        "cancelled": "danger",
    }

    return colors.get(value, "secondary")

@register.filter
def meeting_icon(value):
    """Return fontawesome icon for meeting type"""

    icons = {
        "general": "users",
        "emergency": "exclamation-triangle",
        "committee": "user-friends",
        "planning": "tasks",
        "review": "clipboard-check",
    }

    return icons.get(value, "calendar")

@register.filter
def meeting_status_color(value):
    """
    Return Bootstrap color class based on meeting status
    Example mapping:
        scheduled -> primary
        completed -> success
        cancelled -> danger
    """
    colors = {
        "scheduled": "primary",
        "completed": "success",
        "cancelled": "danger",
        "pending": "warning",
    }
    return colors.get(value, "secondary")





@register.filter
def method_color(method):
    """Return Bootstrap color class for check-in method"""
    color_map = {
        'qr_code': 'success',
        'manual': 'warning',
        'automatic': 'info',
        'api': 'primary',
    }
    return color_map.get(method, 'secondary')


@register.filter
def event_color(event_type):
    """Return Bootstrap color class for event type"""
    color_map = {
        'orientation': 'primary',
        'health_screening': 'success',
        'general_meeting': 'info',
        'seminar': 'warning',
        'social': 'danger',
        'other': 'secondary',
    }
    return color_map.get(event_type, 'secondary')


@register.filter
def session_type_color(session_type):
    """Return Bootstrap color class for session type"""
    color_map = {
        'main': 'primary',
        'workshop': 'success',
        'breakout': 'info',
        'plenary': 'warning',
        'poster': 'danger',
        'other': 'secondary',
    }
    return color_map.get(session_type, 'secondary')


@register.filter
def attendance_status_color(status):
    """Return Bootstrap color class for attendance status"""
    if status:
        return 'success'
    return 'warning'


@register.filter
def priority_color(priority):
    """Return Bootstrap color class for priority"""
    color_map = {
        'high': 'danger',
        'medium': 'warning',
        'low': 'info',
        'urgent': 'danger',
    }
    return color_map.get(priority, 'secondary')


@register.filter
def status_color(status):
    """Return Bootstrap color class for status"""
    color_map = {
        'pending': 'warning',
        'in_progress': 'info',
        'completed': 'success',
        'approved': 'success',
        'rejected': 'danger',
        'cancelled': 'secondary',
        'active': 'success',
        'inactive': 'secondary',
    }
    return color_map.get(status, 'secondary')


@register.filter
def complaint_type_color(complaint_type):
    """Return Bootstrap color class for complaint type"""
    color_map = {
        'academic': 'primary',
        'lecturer': 'warning',
        'association': 'info',
        'facility': 'danger',
        'suggestion': 'success',
        'other': 'secondary',
    }
    return color_map.get(complaint_type, 'secondary')


@register.filter
def meeting_type_color(meeting_type):
    """Return Bootstrap color class for meeting type"""
    color_map = {
        'regular': 'primary',
        'emergency': 'danger',
        'planning': 'success',
        'review': 'info',
        'general': 'warning',
    }
    return color_map.get(meeting_type, 'secondary')


@register.filter
def meeting_status_color(status):
    """Return Bootstrap color class for meeting status"""
    color_map = {
        'scheduled': 'primary',
        'ongoing': 'success',
        'completed': 'secondary',
        'cancelled': 'danger',
        'postponed': 'warning',
    }
    return color_map.get(status, 'secondary')


@register.filter
def task_priority_color(priority):
    """Return Bootstrap color class for task priority"""
    color_map = {
        'high': 'danger',
        'medium': 'warning',
        'low': 'info',
    }
    return color_map.get(priority, 'secondary')


@register.filter
def task_status_color(status):
    """Return Bootstrap color class for task status"""
    color_map = {
        'pending': 'warning',
        'in_progress': 'info',
        'completed': 'success',
        'overdue': 'danger',
        'cancelled': 'secondary',
    }
    return color_map.get(status, 'secondary')


@register.filter
def activity_color(action_type):
    """Return Bootstrap color class for activity type"""
    color_map = {
        'login': 'success',
        'logout': 'secondary',
        'password_change': 'warning',
        'payment': 'info',
        'course_registration': 'primary',
        'file_upload': 'info',
        'admin_action': 'danger',
        'executive_action': 'warning',
        'meeting_created': 'primary',
        'attendance_marked': 'success',
    }
    return color_map.get(action_type, 'secondary')


@register.filter
def activity_icon(action_type):
    """Return Font Awesome icon for activity type"""
    icon_map = {
        'login': 'sign-in-alt',
        'logout': 'sign-out-alt',
        'password_change': 'key',
        'payment': 'credit-card',
        'course_registration': 'book',
        'file_upload': 'upload',
        'admin_action': 'user-shield',
        'executive_action': 'user-tie',
        'meeting_created': 'calendar-plus',
        'attendance_marked': 'check-circle',
    }
    return icon_map.get(action_type, 'circle')


@register.filter
def meeting_icon(meeting_type):
    """Return Font Awesome icon for meeting type"""
    icon_map = {
        'regular': 'calendar',
        'emergency': 'exclamation-triangle',
        'planning': 'clipboard-list',
        'review': 'search',
        'general': 'users',
    }
    return icon_map.get(meeting_type, 'calendar')


@register.simple_tag
def attendance_percentage(checked_in, total):
    """Calculate attendance percentage"""
    if total and total > 0:
        return f"{(checked_in / total * 100):.1f}"
    return "0.0"


@register.simple_tag
def yes_no_icon(value):
    """Return check or times icon based on boolean value"""
    if value:
        return '<i class="fas fa-check-circle text-success"></i>'
    return '<i class="fas fa-times-circle text-danger"></i>'

@register.filter
def activity_color(action_type):
    """Return bootstrap color based on activity type"""
    colors = {
        'create': 'success',
        'update': 'primary',
        'delete': 'danger',
        'login': 'info',
        'logout': 'secondary',
        'payment': 'warning',
    }
    return colors.get(action_type, 'dark')


@register.filter
def activity_icon(action_type):
    """Return fontawesome icon for activity"""
    icons = {
        'create': 'plus',
        'update': 'edit',
        'delete': 'trash',
        'login': 'sign-in-alt',
        'logout': 'sign-out-alt',
        'payment': 'credit-card',
    }
    return icons.get(action_type, 'info-circle')
    
# core/templatetags/core_filters.py

@register.filter
def clean_richtext(value):
    if not value:
        return ''
    soup = BeautifulSoup(value, 'html.parser')
    for elem in soup.find_all(text=True):
        elem.replace_with(elem.replace('\xa0', ' ').strip())
    return str(soup)



@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using the key"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def get_attribute(obj, attr):
    """Get an attribute from an object dynamically"""
    if obj is None:
        return None
    return getattr(obj, attr, None)

@register.filter
def in_list(value, the_list):
    """Check if value is in list"""
    return value in the_list

@register.filter
def index(List, i):
    """Get item from list by index"""
    try:
        return List[int(i)]
    except (IndexError, ValueError, TypeError):
        return None

@register.filter
def multiply(value, arg):
    """Multiply value by argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0



# accounts/templatetags/accounts_tags.py (add these functions)

@register.filter
def task_priority_color(priority):
    """Return Bootstrap color class for task priority"""
    color_map = {
        'high': 'danger',
        'medium': 'warning',
        'low': 'success',
        'urgent': 'danger',
        'normal': 'info',
    }
    return color_map.get(priority, 'secondary')

@register.filter
def task_status_color(status):
    """Return Bootstrap color class for task status"""
    color_map = {
        'pending': 'warning',
        'in_progress': 'info',
        'completed': 'success',
        'cancelled': 'secondary',
        'overdue': 'danger',
    }
    return color_map.get(status, 'secondary')

@register.filter
def task_progress_color(progress):
    """Return Bootstrap color class based on progress percentage"""
    try:
        progress = int(progress)
        if progress >= 75:
            return 'success'
        elif progress >= 50:
            return 'info'
        elif progress >= 25:
            return 'warning'
        else:
            return 'danger'
    except (ValueError, TypeError):
        return 'secondary'

@register.filter
def task_icon(priority):
    """Return icon class for task priority"""
    icon_map = {
        'high': 'fas fa-exclamation-circle text-danger',
        'medium': 'fas fa-flag text-warning',
        'low': 'fas fa-check-circle text-success',
        'urgent': 'fas fa-bell text-danger',
        'normal': 'fas fa-tasks text-info',
    }
    return icon_map.get(priority, 'fas fa-tasks')

@register.filter
def days_overdue(due_date):
    """Return days overdue if task is past due date"""
    from django.utils import timezone
    if not due_date:
        return 0
    
    if due_date < timezone.now().date():
        delta = timezone.now().date() - due_date
        return delta.days
    return 0

@register.filter
def is_overdue(task):
    """Check if task is overdue"""
    from django.utils import timezone
    if not task.due_date or task.status == 'completed':
        return False
    
    if task.due_date < timezone.now().date() and task.status != 'completed':
        return True
    return False
    


# core/templatetags/core_tags.py (add these functions)

@register.filter
def task_priority_color(priority):
    """Return Bootstrap color class for task priority"""
    color_map = {
        'high': 'danger',
        'medium': 'warning',
        'low': 'success',
        'urgent': 'danger',
        'normal': 'info',
    }
    return color_map.get(priority, 'secondary')

@register.filter
def task_status_color(status):
    """Return Bootstrap color class for task status"""
    color_map = {
        'pending': 'warning',
        'in_progress': 'info',
        'completed': 'success',
        'cancelled': 'secondary',
        'overdue': 'danger',
    }
    return color_map.get(status, 'secondary')

@register.filter
def progress_color(percentage):
    """Return Bootstrap color class based on progress percentage"""
    try:
        percentage = int(percentage)
        if percentage >= 75:
            return 'success'
        elif percentage >= 50:
            return 'info'
        elif percentage >= 25:
            return 'warning'
        else:
            return 'danger'
    except (ValueError, TypeError):
        return 'secondary'
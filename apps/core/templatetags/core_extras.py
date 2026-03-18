from django import template

register = template.Library()


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
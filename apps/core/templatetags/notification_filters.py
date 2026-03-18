from django import template

register = template.Library()


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
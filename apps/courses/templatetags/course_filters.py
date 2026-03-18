from django import template

register = template.Library()


@register.filter
def material_icon(material_type):
    icons = {
        "pdf": "file-pdf",
        "video": "video",
        "doc": "file-word",
        "ppt": "file-powerpoint",
        "image": "image",
        "link": "link",
        "zip": "file-archive",
    }
    return icons.get(material_type, "file")


@register.filter
def level_color(level):
    colors = {
        "100": "primary",
        "200": "success",
        "300": "warning",
        "400": "danger",
    }
    return colors.get(level, "secondary")


@register.filter
def event_color(event_type):
    colors = {
        "meeting": "primary",
        "seminar": "success",
        "workshop": "warning",
        "conference": "danger",
        "general": "info",
    }
    return colors.get(event_type, "secondary")
# core/templatetags/core_filters.py
from django import template
from bs4 import BeautifulSoup

register = template.Library()

@register.filter
def clean_richtext(value):
    if not value:
        return ''
    soup = BeautifulSoup(value, 'html.parser')
    for elem in soup.find_all(text=True):
        elem.replace_with(elem.replace('\xa0', ' ').strip())
    return str(soup)
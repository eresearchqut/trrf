from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def show_banner():
    return settings.SHOW_BANNER

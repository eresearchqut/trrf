from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag()
def curator_email():
    return settings.CURATOR_EMAIL

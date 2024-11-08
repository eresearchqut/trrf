from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def is_staging_env():
    return settings.STAGING

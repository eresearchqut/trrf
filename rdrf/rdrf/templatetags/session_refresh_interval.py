from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def session_refresh_interval():
    # 15 seconds before session expiration in ms
    return (settings.SESSION_COOKIE_AGE - settings.SESSION_REFRESH_LEAD_TIME) * 1000

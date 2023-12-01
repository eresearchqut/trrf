from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def session_refresh_interval():
    # Interval is every X seconds (SESSION_REFRESH_LEAD_TIME), before the session is due to expire (SESSION_COOKIE_AGE)
    return (settings.SESSION_COOKIE_AGE - settings.SESSION_REFRESH_LEAD_TIME) * 1000

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def session_refresh_lead_time():
    return settings.SESSION_REFRESH_LEAD_TIME

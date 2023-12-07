from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag()
def session_info():
    return {'max_session_age': settings.SESSION_COOKIE_AGE,
            'warning_lead_time': settings.SESSION_EXPIRY_WARNING_LEAD_TIME,
            'refresh_lead_time': settings.SESSION_REFRESH_LEAD_TIME}

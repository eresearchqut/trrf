from django import template
from django.conf import settings
register = template.Library()


@register.simple_tag
def get_language_settings_codes():
    return [code for code, name in settings.LANGUAGES]

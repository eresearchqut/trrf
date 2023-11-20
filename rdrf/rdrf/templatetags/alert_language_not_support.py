from django import template
from django.conf import settings

register = template.Library()


@register.filter()
def alert_language_not_support(language):
    return language not in [language_code.lower() for language_code in dict(settings.LANGUAGES).keys()]

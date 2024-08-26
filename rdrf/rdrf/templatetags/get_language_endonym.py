from django import template

from rdrf import settings

register = template.Library()


@register.filter()
def get_language_endonym(language_code):
    return dict(settings.ALL_LANGUAGES).get(language_code, language_code)

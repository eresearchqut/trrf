from django import template
from django.utils.translation import to_locale

register = template.Library()


@register.filter()
def get_locale(language):
    return to_locale(language)

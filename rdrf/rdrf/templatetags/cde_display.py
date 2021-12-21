from django import template

from rdrf.helpers.utils import get_display_value

register = template.Library()


@register.filter()
def cde_display_value(value, cde):
    return get_display_value(cde, value)

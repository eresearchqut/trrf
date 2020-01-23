from operator import attrgetter

import pycountry
from django import template

register = template.Library()


@register.simple_tag
def countries():
    return sorted(pycountry.countries, key=attrgetter('name'))

from django import template

from rdrf.helpers.utils import mongo_key
from report.forms import get_cde_field_value

register = template.Library()


@register.simple_tag
def get_cde_value(cfg, form, section, cde):
    return get_cde_field_value(
        cfg, mongo_key(form.name, section.code, cde.code)
    )

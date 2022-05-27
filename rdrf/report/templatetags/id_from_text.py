import re

from django import template

register = template.Library()


@register.simple_tag
def id_from_text(text):
    return re.sub(r"[^a-zA-Z0-9]", "_", text)

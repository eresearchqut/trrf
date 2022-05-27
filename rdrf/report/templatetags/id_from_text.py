from django import template

register = template.Library()


@register.simple_tag
def id_from_text(text):
    return text.replace(" ", "")
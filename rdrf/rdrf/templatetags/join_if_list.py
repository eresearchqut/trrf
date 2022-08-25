from django import template

register = template.Library()


@register.filter()
def join_if_list(list_or_value, separator=", "):
    if isinstance(list_or_value, list):
        return separator.join(list_or_value)
    else:
        return list_or_value

from django import template

register = template.Library()


@register.filter()
def join_if_list(list_or_value, separator=", "):
    if list_or_value and isinstance(list_or_value, list):
        list_as_str = [str(item) for item in list_or_value]
        return separator.join(list_as_str)
    else:
        return list_or_value

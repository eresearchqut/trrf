from django import template

register = template.Library()


@register.filter()
def join_if_list(list_or_value, separator=", ", none_text='None'):
    if list_or_value:
        if isinstance(list_or_value, list):
            list_as_str = [str(item) for item in list_or_value]
            return separator.join(list_as_str)

    return list_or_value if list_or_value else none_text

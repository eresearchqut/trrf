from django import template

register = template.Library()

@register.filter()
def array_item(arr, item):
    try:
        index = int(item)
        if arr and index < len(arr):
            return arr[index]
    except ValueError:
        return None

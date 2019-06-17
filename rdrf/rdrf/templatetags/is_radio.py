from django import template
from django.forms.widgets import RadioSelect

register = template.Library()


@register.filter(name='is_radio')
def is_radio(element):
    if hasattr(element, "field"):
        field = element.field

    field_class_name = field.widget.__class__.__name__
    radio_select_class_names = (RadioSelect().__class__.__name__,)

    return field_class_name in radio_select_class_names

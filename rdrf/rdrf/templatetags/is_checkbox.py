from django import template
from django.forms import CheckboxInput
from django.forms.widgets import CheckboxSelectMultiple

register = template.Library()


@register.filter(name='is_checkbox')
def is_checkbox(element):
    """
    Depending on the template the input can be an element wrapper with a field attribute
    or a field object directly.
    """
    if hasattr(element, "field"):
        field = element.field

    field_class_name = field.widget.__class__.__name__
    checkbox_class_names = (CheckboxInput().__class__.__name__, CheckboxSelectMultiple().__class__.__name__, )

    return field_class_name in checkbox_class_names

from django import template

register = template.Library()


@register.filter(name="is_checkbox")
def is_checkbox(element):
    """
    Depending on the template the input can be an element wrapper with a field attribute
    or a field object directly.
    """
    if hasattr(element, "field"):
        field = element.field
        return field.widget.input_type == "checkbox"

    return False

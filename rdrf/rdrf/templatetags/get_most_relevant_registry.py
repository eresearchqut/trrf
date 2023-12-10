from django import template
from rdrf.models.definition.models import Registry

register = template.Library()


@register.filter
def get_most_relevant_registry(registry_code, user):
    all_registries = Registry.objects.all()
    registry = None

    if registry_code:
        registry = all_registries.get(code=registry_code)
    elif all_registries.count() == 1:
        registry = all_registries.first()
    elif not user.is_anonymous:
        registry = user.my_registry

    return registry

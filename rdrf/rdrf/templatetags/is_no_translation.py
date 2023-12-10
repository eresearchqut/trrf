from django import template
from rdrf.models.definition.models import Registry

register = template.Library()


@register.filter
def is_no_translation(registry):
    if registry:
        return 'no' if registry.has_feature('no_translation') else 'yes'

    return 'no' if all(registry.has_feature('no_translation') for registry in Registry.objects.all()) else 'yes'

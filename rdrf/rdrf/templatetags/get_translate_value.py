from django import template
from rdrf.models.definition.models import Registry
from rdrf.helpers.registry_features import RegistryFeatures

register = template.Library()


@register.filter
def get_translate_value(registry):
    no_translation = RegistryFeatures.NO_TRANSLATION
    if registry:
        return 'no' if registry.has_feature(no_translation) else 'yes'

    return 'no' if all(registry.has_feature(no_translation) for registry in Registry.objects.all()) else 'yes'

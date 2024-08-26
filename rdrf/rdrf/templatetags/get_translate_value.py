from django import template

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry

register = template.Library()


@register.filter
def get_translate_value(registry):
    if registry:
        return (
            "no"
            if registry.has_feature(RegistryFeatures.NO_TRANSLATION)
            else "yes"
        )

    return (
        "no"
        if all(
            registry.has_feature(RegistryFeatures.NO_TRANSLATION)
            for registry in Registry.objects.all()
        )
        else "yes"
    )

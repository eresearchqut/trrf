from django import template
from rdrf.models.definition.models import Registry
from registry.groups.models import CustomUser
from django.contrib.auth.models import AnonymousUser

register = template.Library()


@register.filter
def no_translation(registry_code, request):
    def get_metadata_features(registry_model):
        return registry_model.metadata.get('features', [])

    all_registries = Registry.objects.all()
    user = request.user
    if registry_code in ['', None]:
        if all_registries.count() == 1:
            return 'no_translation' in get_metadata_features(all_registries.first())
        if not isinstance(user, AnonymousUser):
            for registry in CustomUser.objects.filter(username=user).values('registry'):
                if 'no_translation' not in get_metadata_features(all_registries.filter(id=registry['registry'])[0]):
                    return False
            return True
        return False
    else:
        return 'no_translation' in get_metadata_features(all_registries.filter(code=registry_code)[0])

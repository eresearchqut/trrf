import logging
from functools import wraps

from django.http import Http404

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry

logger = logging.getLogger(__name__)


def is_legacy_reports_enabled(function):
    def any_registry_has_legacy_reports_enabled():
        return any(r.has_feature(RegistryFeatures.LEGACY_REPORTS) for r in Registry.objects.all())

    @wraps(function)
    def _wrapped_view(request, *args, **kwargs):
        if any_registry_has_legacy_reports_enabled():
            return function(request, *args, **kwargs)
        else:
            raise Http404('Explorer reports not enabled')

    return _wrapped_view

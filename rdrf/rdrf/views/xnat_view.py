import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views import View

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.integration.xnat_service import xnat_experiments_scans
from rdrf.models.definition.models import Registry
from rdrf.security.mixins import StaffMemberRequiredMixin

logger = logging.getLogger(__name__)


class XnatScansLookup(StaffMemberRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, registry_code, project_id, subject_id):
        registry = get_object_or_404(Registry, code=registry_code)
        if not registry.has_feature(RegistryFeatures.XNAT_INTEGRATION):
            return JsonResponse({'message': _('XNAT Integration is not enabled for this registry.')}, status=405)

        return JsonResponse({
            'experiments': xnat_experiments_scans(project_id, subject_id)
        })

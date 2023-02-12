import logging

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views import View

from rdrf.integration.xnat_service import xnat_experiments_scans

logger = logging.getLogger(__name__)


class XnatScansLookup(View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, project_id, subject_id):
        return JsonResponse({
            'experiments': xnat_experiments_scans(project_id, subject_id)
        })

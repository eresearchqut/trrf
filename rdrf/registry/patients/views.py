
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic.base import View

from rdrf.db.filestorage import virus_checker_result
from rdrf.helpers.view_helper import FileErrorHandlingMixin
from rdrf.security.security_checks import security_check_user_patient

from .models import PatientConsent


class ConsentFileView(FileErrorHandlingMixin, View):

    def get(self, request, consent_id=None, filename=""):
        consent = get_object_or_404(PatientConsent, pk=consent_id)
        security_check_user_patient(request.user, consent.patient)
        check_status = request.GET.get('check_status', '')
        need_status_check = check_status and check_status.lower() == 'true'
        if need_status_check:
            return JsonResponse({
                "response": virus_checker_result(consent.form.name),
            })

        if consent.form and consent.form.file:
            response = FileResponse(consent.form.file, content_type='application/octet-stream')
            response['Content-disposition'] = "filename=%s" % filename
            return response
        raise Http404("The file %s (consent %s) was not found" % (filename, consent_id))

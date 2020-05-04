from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from rdrf.security.security_checks import security_check_user_patient
from rdrf.helpers.view_helper import FileErrorHandlingView

from .models import PatientConsent


class ConsentFileView(FileErrorHandlingView):

    def with_error_handling(self, request, consent_id=None, filename=""):
        consent = get_object_or_404(PatientConsent, pk=consent_id)
        security_check_user_patient(request.user, consent.patient)
        if consent.form and consent.form.file:
            response = FileResponse(consent.form.file, content_type='application/octet-stream')
            response['Content-disposition'] = "filename=%s" % consent.filename
            return response
        raise Http404("The file %s (consent %s) was not found" % (consent.filename, consent_id))

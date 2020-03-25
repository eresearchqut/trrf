from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import View

from rdrf.security.security_checks import security_check_user_patient

from .models import PatientConsent


class ConsentFileView(LoginRequiredMixin, View):

    def get(self, request, consent_id=None, filename=""):
        consent = get_object_or_404(PatientConsent, pk=consent_id)
        security_check_user_patient(request.user, consent.patient)
        if consent.form and consent.form.file:
            response = FileResponse(consent.form.file, content_type='application/octet-stream')
            response['Content-disposition'] = "filename=%s" % consent.filename
            return response
        raise Http404("The file %s (consent %s) was not found" % (consent.filename, consent_id))

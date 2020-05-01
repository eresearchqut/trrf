from django.core.serializers.json import DjangoJSONEncoder
import json

from django.views.generic.base import View
from django.shortcuts import render
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _

from registry.patients.models import ConsentValue
from registry.patients.models import Patient

from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import ConsentQuestion
from rdrf.models.definition.models import Registry

from rdrf.security.security_checks import security_check_user_patient, get_object_or_permission_denied
from rdrf.security.mixins import StaffMemberRequiredMixin


class ConsentList(StaffMemberRequiredMixin, View):

    def _get_template(self):
        return 'rdrf_cdes/consent_list.html'

    def get(self, request, registry_code):
        if not (request.user.is_superuser or request.user.registry.filter(code=registry_code).exists()):
            raise PermissionDenied

        context = {}

        consent_sections = ConsentSection.objects.filter(registry__code=registry_code)
        if request.user.is_superuser:
            patients = Patient.objects.filter(rdrf_registry__code=registry_code, active=True)
        else:
            patients = Patient.objects.filter(
                rdrf_registry__code=registry_code,
                working_groups__in=request.user.working_groups.all(),
                active=True)

        patient_list = {}
        for patient in patients:
            sections = {}
            for consent_section in consent_sections:
                if consent_section.applicable_to(patient):
                    answers = []
                    first_saves = []
                    last_updates = []
                    questions = ConsentQuestion.objects.filter(section=consent_section)
                    for question in questions:
                        try:
                            cv = ConsentValue.objects.get(
                                patient=patient, consent_question=question)
                            answers.append(cv.answer)
                            if cv.first_save:
                                first_saves.append(cv.first_save)
                            if cv.last_update:
                                last_updates.append(cv.last_update)
                        except ConsentValue.DoesNotExist:
                            answers.append(False)
                    first_save = min(first_saves) if first_saves else None
                    last_update = max(last_updates) if last_updates else None
                    sections[consent_section] = {
                        "first_save": first_save,
                        "last_update": last_update,
                        "signed": all(answers)
                    }
            patient_list[patient] = sections

        context['consents'] = patient_list
        context['registry'] = Registry.objects.get(code=registry_code).name
        context['registry_code'] = registry_code

        return render(request, self._get_template(), context)


class PrintConsentList(ConsentList):

    def _get_template(self):
        return 'rdrf_cdes/consent_list_print.html'


class ConsentDetails(StaffMemberRequiredMixin, View):

    def get(self, request, registry_code, section_id, patient_id):
        patient_model = get_object_or_permission_denied(Patient, pk=patient_id)
        security_check_user_patient(request.user, patient_model)

        if request.is_ajax:
            values = self._get_consent_details_for_patient(
                registry_code, section_id, patient_id)
            return HttpResponse(json.dumps(values, cls=DjangoJSONEncoder))

        return render(request, 'rdrf_cdes/consent_details.html', {})

    def _get_consent_details_for_patient(self, registry_code, section_id, patient_id):
        consent_questions = ConsentQuestion.objects.filter(
            section__id=section_id, section__registry__code=registry_code)

        values = []
        for consent_question in consent_questions:
            try:
                consent_value = ConsentValue.objects.get(
                    consent_question=consent_question, patient__id=patient_id)
                answer = consent_value.answer
                values.append({
                    "question": _(consent_question.question_label),
                    "answer": answer,
                    "patient_id": patient_id,
                    "section_id": section_id,
                    "first_save": consent_value.first_save,
                    "last_update": consent_value.last_update
                })
            except ConsentValue.DoesNotExist:
                values.append({
                    "question": _(consent_question.question_label),
                    "answer": False,
                    "patient_id": patient_id,
                    "section_id": section_id
                })
        return values

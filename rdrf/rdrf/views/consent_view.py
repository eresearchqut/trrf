from django.db.models import Min, Max, Count, Case, When, F
from django.views.generic.base import View
from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _

from registry.patients.models import ConsentValue
from registry.patients.models import Patient

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

        if request.user.is_superuser:
            patients = Patient.objects.filter(rdrf_registry__code=registry_code, active=True)
        else:
            patients = Patient.objects.filter(
                rdrf_registry__code=registry_code,
                working_groups__in=request.user.working_groups.all(),
                active=True)

        # Aggregate consent values by Patient and ConsentSection
        consents = patients.annotate(
            consent_section_id=F('consents__consent_question__section__id'),
            consent_section_label=F('consents__consent_question__section__section_label'),
            first_save=Min('consents__first_save'),
            last_update=Max('consents__last_update'),
            cnt_total_questions=Count('consents__consent_question'),
            cnt_completed_answers=Count(Case(When(consents__answer=True, then=1)))
        ).filter(
            consent_section_label__isnull=False
        )

        context['consents'] = consents
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

        return JsonResponse({
            "data": self._get_consent_details_for_patient(registry_code, section_id, patient_id)
        })

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

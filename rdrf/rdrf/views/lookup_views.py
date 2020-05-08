import logging

from django.http import JsonResponse
from django.views.generic import View
from django.urls import reverse

from registry.patients.models import Patient

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.security.mixins import StaffMemberRequiredMixin


logger = logging.getLogger(__name__)


class PatientLookup(StaffMemberRequiredMixin, View):

    def get(self, request, reg_code):
        from rdrf.models.definition.models import Registry
        from registry.patients.models import Patient
        from registry.groups.models import WorkingGroup
        from django.db.models import Q

        term = None
        results = []

        try:
            registry_model = Registry.objects.get(code=reg_code)
            if registry_model.has_feature(RegistryFeatures.QUESTIONNAIRES):
                term = request.GET.get("term", "")
                if not request.user.is_superuser:
                    working_groups = [wg for wg in request.user.working_groups.all()]
                else:
                    working_groups = [
                        wg for wg in WorkingGroup.objects.filter(
                            registry=registry_model)]

                query = (Q(given_names__icontains=term) | Q(family_name__icontains=term)) & \
                    Q(working_groups__in=working_groups)

                for patient_model in Patient.objects.filter(query):
                    if patient_model.active:
                        name = "%s" % patient_model
                        results.append({"value": patient_model.pk, "label": name,
                                        "class": "Patient", "pk": patient_model.pk})

        except Registry.DoesNotExist:
            results = []

        return JsonResponse(results, safe=False)


class FamilyLookup(View):

    def _patient_info(self, patient, working_group, link, relationship=None):
        ret_val = {
            "pk": patient.pk,
            "given_names": patient.given_names,
            "family_name": patient.family_name,
            "class": 'Patient' if not relationship else 'PatientRelative',
            "working_group": working_group,
            "link": link
        }
        if relationship:
            ret_val.update({
                'relationship': relationship
            })
        return ret_val

    def get(self, request, reg_code, index=None):
        result = {}
        try:
            index_patient_pk = request.GET.get("index_pk", None)
            patient = Patient.objects.get(pk=index_patient_pk)
        except Patient.DoesNotExist:
            result = {"error": "patient does not exist"}
            return JsonResponse(result)

        if not patient.is_index:
            result = {"error": "patient is not an index"}
            return JsonResponse(result)

        if not request.user.can_view_patient_link(patient):
            result = {"error": "User cannot view patient link"}
            return JsonResponse(result)

        link = reverse("patient_edit", args=[reg_code, patient.pk])
        working_group = None

        result["index"] = self._patient_info(patient, working_group, link)
        result["relatives"] = []

        result["relationships"] = self._get_relationships()

        for relative in patient.relatives.all():
            patient_created = relative.relative_patient
            working_group = None
            relative_link = None
            if patient_created and request.user.can_view_patient_link(patient_created):
                relative_link = reverse("patient_edit", args=[reg_code, patient_created.pk])

            if relative_link:
                working_group = self._get_working_group_name(patient_created)
                result["relatives"].append(
                    self._patient_info(relative, working_group, relative_link, relative.relationship)
                )

        return JsonResponse(result)

    def _get_relationships(self):
        from registry.patients.models import PatientRelative
        return [pair[0] for pair in PatientRelative.RELATIVE_TYPES]

    def _get_working_group_name(self, patient_model):
        return ",".join(sorted([wg.name for wg in patient_model.working_groups.all()]))

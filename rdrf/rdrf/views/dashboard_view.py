import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views import View

from rdrf.models.definition.models import Registry, ConsentSection, RegistryDashboard
from registry.patients.models import Patient, ParentGuardian
from registry.patients.parent_view import BaseParentView

logger = logging.getLogger(__name__)


class DashboardListView(View):
    def get(self, request):
        try:
            parent = ParentGuardian.objects.get(user=request.user)
        except ParentGuardian.DoesNotExist:
            raise Http404(_("No Dashboards for this user"))

        registries = get_parent_patient_registries(parent).all()
        registry_dashboards = RegistryDashboard.objects.filter(registry__in=registries)

        if len(registry_dashboards) == 1:
            return redirect(reverse('parent_dashboard', args=[registries.first().code]))

        context = {
            'registries': registries
        }

        return render(request, 'dashboard/dashboards_list.html', context)


class ParentDashboardView(BaseParentView):
    def get(self, request, registry_code):
        registry = get_object_or_404(Registry, code=registry_code)
        dashboard = get_object_or_404(RegistryDashboard, registry=registry)

        patients = [patient for patient in self.parent.children if [registry in patient.rdrf_registry.all()]]

        patient_id = request.GET.get('patient_id')
        if patient_id:
            patient = get_object_or_404(Patient, pk=patient_id)
            if request.user.is_parent and patient not in patients:
                raise PermissionDenied
        else:
            if len(patients) > 0:
                patient = patients[0]

        context = {'parent': self.parent,
                   'registry': registry,
                   'dashboard': get_dashboard_dict(dashboard, registry, patient),
                   'patients': patients,
                   'patient': patient,
                   'consent_status': get_patient_consent_status(patient, registry)}

        return render(request, 'dashboard/parent_dashboard.html', context)


class ParentPatientDashboardView(BaseParentView):
    def get(self, request, registry_code, patient_id):
        return render(request, 'dashboard/parent_dashboard.html', {})


def get_parent_patient_registries(parent):
    return Registry.objects.filter(patients__in=parent.children).distinct()


def get_patient_consent_status(patient, registry):
    registry_consent_questions = [question
                                  for section in ConsentSection.objects.filter(registry=registry).all()
                                  for question in section.questions.all()]
    total_registry_consents = len(registry_consent_questions)
    return {
        'completed': 0,
        'total': total_registry_consents
    }


def get_dashboard_dict(dashboard, registry, patient):
    dd_dict = {
        'model': dashboard,
        'widgets': {widget.widget_type: {
            'title': widget.title,
            'free_text': widget.free_text,
            'form_links': [{'label': link.label, 'url': link.registry_form.get_link(patient, patient.default_context(registry))}
                           for link in widget.links.all()]
        } for widget in dashboard.widgets.all()},

    }

    logger.info(dd_dict)
    return dd_dict

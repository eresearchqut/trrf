import logging

from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.utils.translation import ugettext as _

from rdrf.models.definition.models import Registry
from rdrf.security.mixins import SuperuserRequiredMixin
from registry.patients.models import Patient, ParentGuardian

logger = logging.getLogger(__name__)


class DashboardConfigView(SuperuserRequiredMixin, View):
    def get(self, request):
        context = {}
        return render(request, 'dashboard/admin_configuration.html', context)


class DashboardListView(View):
    def get(self, request):
        try:
            parent = ParentGuardian.objects.get(user=request.user)
        except ParentGuardian.DoesNotExist:
            raise Http404(_("No Dashboards for this user"))

        # TODO also need to check if the registries have a dashboard configured.
        registries = get_parent_patient_registries(parent).all()

        logger.info(f'1. registry count: {len(registries)}')

        if len(registries) == 1:
            return redirect(reverse('dashboard', args=[registries.first().code]))

        logger.info(f'2a. registry count: {len(registries)}')

        context = {
            'registries': registries
        }
        return render(request, 'dashboard/dashboards_list.html', context)


class DashboardView(View):
    def get(self, request, registry_code):
        registry = get_object_or_404(Registry, code=registry_code)
        patients = Patient.objects.get_by_user_and_registry(request.user, registry)

        context = {'registry': registry, 'patients': patients}
        return render(request, 'dashboard/dashboard_parent.html', context)


class ParentPatientDashboardView(View):
    def get(self, request, registry_code, patient_id):
        return render(request, 'dashboard/dashboard_parent.html', {})


def get_parent_patient_registries(parent):
    return Registry.objects.filter(patients__in=parent.children)

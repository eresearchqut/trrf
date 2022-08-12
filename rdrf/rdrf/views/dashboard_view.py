import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views import View

from rdrf.helpers.utils import consent_status_for_patient
from rdrf.models.definition.models import Registry, RegistryDashboard, ContextFormGroup, Section, \
    RDRFContext, ConsentQuestion
from rdrf.reports.generator import get_clinical_data
from registry.patients.models import Patient, ParentGuardian, ConsentValue
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
                   'dashboard': dashboard_config(dashboard, registry, patient),
                   'patients': patients,
                   'patient': patient,
                   'consent_status': patient_consent_summary(patient, registry)}

        return render(request, 'dashboard/parent_dashboard.html', context)


def get_parent_patient_registries(parent):
    return Registry.objects.filter(patients__in=parent.children).distinct()


def patient_consent_summary(patient, registry):

    registry_consent_questions = ConsentQuestion.objects.filter(section__registry=registry)
    patient_consents = ConsentValue.objects.filter(patient=patient, consent_question__section__registry=registry)

    return {
        'valid': consent_status_for_patient(registry.code, patient),
        'completed': patient_consents.count(),
        'total': registry_consent_questions.count()
    }


def dashboard_config(dashboard, registry, patient):

    contexts = contexts_by_group(patient, registry)

    dd_dict = {
        'model': dashboard,
        'widgets': {widget.widget_type: {
            'title': widget.title,
            'free_text': widget.free_text,
            'form_links': [{'label': link.label,
                            'url': get_form_link(patient, contexts, registry, link.cfg_code, link.registry_form)}
                           for link in widget.links.all()],
            'clinical_data': [{'label': cde.label,
                               'data': get_cde_data(patient, contexts, registry, cde.cfg_code, cde.form_name, cde.section_code, cde.cde_code)}
                              for cde in widget.cdes.all()]
        } for widget in dashboard.widgets.all()}
    }

    logger.info(dd_dict)
    return dd_dict


def get_form_link(patient, contexts, registry, cfg_code, registry_form):
    logger.info('get form link ~')
    cfg = ContextFormGroup.objects.get(code=cfg_code)

    context = get_context(patient, registry, cfg, contexts)

    if context:
        return registry_form.get_link(patient, context)

    if cfg.is_multiple:
        return cfg.get_add_action(patient)


def get_cde_data(patient, contexts, registry, cfg_code, form_name, section_code, cde_code):
    cfg = ContextFormGroup.objects.get(code=cfg_code)
    section = Section.objects.get(code=section_code)

    logger.info(cfg)
    context = get_context(patient, registry, cfg, contexts)

    if not context:
        return None

    data = get_clinical_data(registry.code,
                             patient.pk,
                             context.pk)

    if not data:
        return None

    form_value = patient.get_form_value(registry.code,
                                        form_name,
                                        section_code,
                                        cde_code,
                                        multisection=section.allow_multiple,
                                        clinical_data=data)

    return form_value


def get_context(patient, registry, context_form_group, contexts):
    context = contexts.get(context_form_group.id)
    if context:
        return context

    if context_form_group.is_fixed:
        return patient.default_context(patient, registry)

    return None


def contexts_by_group(patient, registry):
    cfgs = ContextFormGroup.objects.filter(registry=registry)
    contexts = RDRFContext.objects.get_for_patient(patient, registry)

    return {context_form_group.id: context
            for context_form_group in cfgs
            for context in contexts.filter(context_form_group=context_form_group).order_by('-last_updated')}


import logging
from collections import defaultdict

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils.formats import date_format
from django.utils.translation import ugettext as _
from django.views import View

from rdrf.forms.progress.form_progress import FormProgress
from rdrf.forms.widgets.widgets import get_widget_class
from rdrf.helpers.utils import consent_status_for_patient
from rdrf.models.definition.models import Registry, RegistryDashboard, ContextFormGroup, RDRFContext, ConsentQuestion
from rdrf.patients.query_data import query_patient
from rdrf.reports.generator import get_clinical_data
from registry.patients.models import Patient, ConsentValue
from registry.patients.parent_view import BaseParentView

logger = logging.getLogger(__name__)


class DashboardListView(View):
    def get(self, request):
        registry_dashboards = RegistryDashboard.objects.filter_user_parent_dashboards(request.user)

        if not registry_dashboards:
            raise Http404(_("No Dashboards for this user"))

        if len(registry_dashboards) == 1:
            return redirect(reverse('parent_dashboard', args=[registry_dashboards.first().registry.code]))

        context = {
            'dashboards': registry_dashboards
        }

        return render(request, 'dashboard/dashboards_list.html', context)


class ParentDashboardView(BaseParentView):
    def get(self, request, registry_code):
        registry = get_object_or_404(Registry, code=registry_code)
        dashboard = get_object_or_404(RegistryDashboard, registry=registry)

        patients = [patient for patient in self.parent.children if registry in patient.rdrf_registry.all()]

        patient_id = request.GET.get('patient_id')
        if patient_id:
            patient = get_object_or_404(Patient, pk=patient_id)
            if request.user.is_parent and patient not in patients:
                raise PermissionDenied
        else:
            if len(patients) > 0:
                patient = patients[0]

        patient_contexts = contexts_by_group(registry, patient)

        context = {'parent': self.parent,
                   'registry': registry,
                   'dashboard': dashboard_config(dashboard, registry, patient, patient_contexts, self.request),
                   'patients': patients,
                   'patient': patient,
                   'consent_status': patient_consent_summary(registry, patient),
                   'module_progress': patient_module_progress(registry, patient, patient_contexts, request.user)
                   }

        return render(request, 'dashboard/parent_dashboard.html', context)


def patient_consent_summary(registry, patient):
    registry_consent_questions = ConsentQuestion.objects.filter(section__registry=registry)
    patient_consents = ConsentValue.objects.filter(patient=patient, consent_question__section__registry=registry)

    return {
        'valid': consent_status_for_patient(registry.code, patient),
        'completed': patient_consents.count(),
        'total': registry_consent_questions.count()
    }


def patient_module_progress(registry, patient, contexts, user):
    form_progress = FormProgress(registry)

    modules_progress = defaultdict(dict)  # {'fixed': {}, 'multi': {}}

    for cfg, context in contexts.items():
        forms_progress = {}
        key = None
        for form in cfg.forms:

            if not (user.can_view(form) and form.has_progress_indicator):
                continue

            progress_dict = {}

            if cfg.is_fixed:
                key = 'fixed'
                progress_dict['link'] = get_form_link(registry, cfg.code, form, patient, contexts=contexts, context=context)
                progress_dict['progress'] = form_progress.get_form_progress(form, patient, context)
            elif cfg.is_multiple:
                key = 'multi'
                last_completed = None

                if context:
                    last_completed = date_format(parse_datetime(patient.get_form_timestamp(form, context)))

                progress_dict['link'] = cfg.get_add_action(patient)[0]
                progress_dict['last_completed'] = last_completed

            forms_progress.update({form: progress_dict})
        if key:
            modules_progress[key].update({cfg: forms_progress})

        logger.info(key)
        logger.info(modules_progress)

    return modules_progress


def dashboard_config(dashboard, registry, patient, contexts, request):
    return {
        'model': dashboard,
        'widgets': {
            widget.widget_type: {
                'title': widget.title,
                'free_text': widget.free_text,
                'form_links': [{'label': link.label,
                                'url': get_form_link(registry, link.context_form_group.code, link.registry_form, patient, contexts=contexts)}
                               for link in widget.links.all()],
                'clinical_data': [{'label': cde.label,
                                   'data': get_cde_data(registry, cde.context_form_group, cde.registry_form,
                                                        cde.section, cde.cde, patient, contexts)}
                                  for cde in widget.cdes.all()],
                'demographic_data': patient_demographic_data(widget, registry, patient, request)
            } for widget in dashboard.widgets.all()
        }
    }


def get_form_link(registry, cfg_code, registry_form, patient, contexts=None, context=None):
    cfg = ContextFormGroup.objects.get(code=cfg_code)

    if not context:
        context = get_context(registry, cfg, patient, contexts)

    if context:
        return registry_form.get_link(patient, context)

    if cfg.is_multiple:
        link, title = cfg.get_add_action(patient)
        return link


def get_cde_data(registry, cfg, form, section, cde, patient, contexts):
    context = get_context(registry, cfg, patient, contexts)

    if not context:
        return None

    data = get_clinical_data.__wrapped__(registry.code,
                                         patient.pk,
                                         context.pk)

    if not data:
        return None

    form_value = patient.get_form_value(registry.code,
                                        form.name,
                                        section.code,
                                        cde.code,
                                        multisection=section.allow_multiple,
                                        clinical_data=data)

    return cde_display_value(cde, form_value)


# TODO put this somewhere common
def cde_display_value(cde_model, value):
    datatype = cde_model.datatype.strip().lower()
    if datatype == 'lookup':
        value = get_widget_class(cde_model.widget_name).denormalized_value(value)
    elif cde_model.pv_group:
        cde_values_dict = cde_model.pv_group.cde_values_dict
        if isinstance(value, list):
            value = [cde_values_dict.get(value_item, value_item) for value_item in value]
        else:
            value = cde_values_dict.get(value, value)

    # Ensure we are returning value as the correct type based on the expected output from the CDE configuration
    if cde_model.allow_multiple:
        return value if isinstance(value, list) else [value]
    else:
        return value


def patient_demographic_data(widget, registry, patient, request):
    # TODO rename to patient_field? or just field
    config = {demographic.patient_demographic_field: demographic.label for demographic in widget.demographics.all()}
    fields = config.keys()
    logger.info(fields)

    if fields:
        result = query_patient(request, registry, patient.id, fields)
        if result:
            return {k: {'label': v, 'value': result.get(k)} for k, v in config.items()}

    return {}


def get_context(registry, context_form_group, patient, contexts):
    context = contexts.get(context_form_group)
    if context:
        return context

    if context_form_group.is_fixed:
        return patient.default_context(patient, registry)

    return None


def contexts_by_group(registry, patient):
    def last_context(context_form_group):
        return contexts.filter(context_form_group=context_form_group).order_by('-last_updated').first()
    context_form_groups = ContextFormGroup.objects.filter(registry=registry)
    contexts = RDRFContext.objects.get_for_patient(patient, registry)

    return {context_form_group: last_context(context_form_group)
            for context_form_group in context_form_groups}

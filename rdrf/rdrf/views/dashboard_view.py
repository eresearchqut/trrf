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
from rdrf.helpers.utils import consent_status_for_patient
from rdrf.models.definition.models import Registry, RegistryDashboard, ContextFormGroup, RDRFContext, ConsentQuestion
from rdrf.patients.query_data import query_patient
from rdrf.reports.generator import get_clinical_data
from registry.patients.models import Patient, ConsentValue, ParentGuardian

logger = logging.getLogger(__name__)


class ParentDashboard(object):
    def __init__(self, request, dashboard, patient):
        self.dashboard = dashboard
        self.registry = dashboard.registry
        self.patient = patient

        self._request = request
        self._contexts = self._load_contexts()

    def _load_contexts(self):
        def last_context(context_form_group):
            return contexts.filter(context_form_group=context_form_group).order_by('-last_updated').first()

        context_form_groups = ContextFormGroup.objects.filter(registry=self.registry)
        contexts = RDRFContext.objects.get_for_patient(self.patient, self.registry)

        return {context_form_group: last_context(context_form_group)
                for context_form_group in context_form_groups}

    def _get_patient_context(self, context_form_group):
        context = self._contexts.get(context_form_group)
        if context:
            return context

        if context_form_group.is_fixed:
            return self.patient.default_context(self.registry)

        return None

    def _get_form_link(self, context_form_group, registry_form, context=None):
        if not context:
            context = self._get_patient_context(context_form_group)

        if context:
            return registry_form.get_link(self.patient, context)

        if context_form_group.is_multiple:
            link, title = context_form_group.get_add_action(self.patient)
            return link

    def _patient_consent_summary(self):
        registry_consent_questions = ConsentQuestion.objects.filter(section__registry=self.registry)
        patient_consents = ConsentValue.objects.filter(patient=self.patient,
                                                       consent_question__section__registry=self.registry)

        return {
            'valid': consent_status_for_patient(self.registry.code, self.patient),
            'completed': patient_consents.count(),
            'total': registry_consent_questions.count()
        }

    def _get_module_progress(self):
        if not self._request.user.has_perm('patients.can_see_data_modules'):
            return None

        form_progress = FormProgress(self.registry)

        modules_progress = defaultdict(dict)  # {'fixed': {}, 'multi': {}}

        for cfg, context in self._contexts.items():
            forms_progress = {}
            key = None
            for form in cfg.forms:
                if not (self._request.user.can_view(form)):
                    continue

                progress_dict = {}

                if cfg.is_fixed:
                    if not form.has_progress_indicator:
                        continue

                    key = 'fixed'
                    progress_dict['link'] = self._get_form_link(cfg, form, context=context)
                    progress_dict['progress'] = form_progress.get_form_progress(form, self.patient, context)
                elif cfg.is_multiple:
                    key = 'multi'
                    last_completed = None

                    if context:
                        form_timestamp = self.patient.get_form_timestamp(form, context)
                        if form_timestamp:
                            last_completed = date_format(parse_datetime(self.patient.get_form_timestamp(form, context)))

                    progress_dict['link'] = cfg.get_add_action(self.patient)[0]
                    progress_dict['last_completed'] = last_completed or None

                forms_progress.update({form: progress_dict})
            if key:
                modules_progress[key].update({cfg: forms_progress})

        return modules_progress

    def _get_cde_data(self, cfg, form, section, cde):
        context = self._get_patient_context(cfg)

        if not context:
            return None

        data = get_clinical_data.__wrapped__(self.registry.code,
                                             self.patient.pk,
                                             context.pk)

        if not data:
            return None

        form_value = self.patient.get_form_value(self.registry.code,
                                                 form.name,
                                                 section.code,
                                                 cde.code,
                                                 multisection=section.allow_multiple,
                                                 clinical_data=data)

        return cde.display_value(form_value)

    def _get_demographic_data(self, widget):
        config = {demographic.field: _(demographic.label)
                  for demographic in widget.demographics.all() if demographic.model == 'patient'}
        fields = config.keys()

        if fields:
            result = query_patient(self._request, self.registry, self.patient.id, fields)
            if result:
                return {k: {'label': v, 'value': result.get(k)} for k, v in config.items()}

        return {}

    def _get_widget_summary(self):
        return {
            widget.widget_type: {
                'title': _(widget.title),
                'free_text': _(widget.free_text),
                'form_links': [{'label': _(link.label),
                                'url': self._get_form_link(link.context_form_group, link.registry_form)}
                               for link in widget.links.all()],
                'clinical_data': [{'label': _(cde.label),
                                   'data': self._get_cde_data(cde.context_form_group,
                                                              cde.registry_form,
                                                              cde.section,
                                                              cde.cde)}
                                  for cde in widget.cdes.all()],
                'demographic_data': self._get_demographic_data(widget)
            } for widget in self.dashboard.widgets.all()
        }

    def template(self):
        return {
            'registry': self.registry,
            'patient': self.patient,
            'patient_status': {
                'consent': self._patient_consent_summary(),
                'module_progress': self._get_module_progress()
            },
            'widgets': self._get_widget_summary()
        }


class BaseDashboardView(View):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = None
        self.parent = None

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        registry_code = kwargs.get('registry_code')

        if registry_code:
            self.registry = get_object_or_404(Registry, code=kwargs['registry_code'])
            if not request.user.in_registry(self.registry):
                raise PermissionDenied

        user_allowed = user.is_superuser or user.is_parent
        if not user_allowed:
            raise PermissionDenied

        if user.is_superuser:
            parent_id = request.GET.get('parent_id')
            if parent_id:
                self.parent = get_object_or_404(ParentGuardian, pk=parent_id)
        else:
            self.parent = ParentGuardian.objects.filter(user=user).first()
            if not self.parent and user.is_parent:
                raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class DashboardListView(BaseDashboardView):
    def get(self, request):
        if request.user.is_superuser:
            dashboards = self.parent.user.dashboards
        else:
            dashboards = request.user.dashboards

        if not dashboards:
            raise Http404(_("No Dashboards for this user"))

        if len(dashboards) == 1:
            return redirect(reverse('parent_dashboard', args=[dashboards.first().registry.code]))

        context = {
            'dashboards': dashboards
        }

        return render(request, 'dashboard/dashboards_list.html', context)


class ParentDashboardView(BaseDashboardView):
    def get(self, request, registry_code):
        dashboard = get_object_or_404(RegistryDashboard, registry=self.registry)

        patients = [patient for patient in self.parent.children if self.registry in patient.rdrf_registry.all()]

        patient_id = request.GET.get('patient_id')
        if patient_id:
            patient = get_object_or_404(Patient, pk=patient_id)
            if request.user.is_parent and patient not in patients:
                raise PermissionDenied
        else:
            if len(patients) > 0:
                patient = patients[0]

        context = {
            'parent': self.parent,
            'patients': patients,
            'dashboard': ParentDashboard(request, dashboard, patient).template()
        }

        return render(request, 'dashboard/parent_dashboard.html', context)

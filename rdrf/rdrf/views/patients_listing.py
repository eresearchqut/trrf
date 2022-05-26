import json
import logging
from itertools import chain

from django.core.exceptions import PermissionDenied
from django.core.paginator import InvalidPage, Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.context_processors import csrf
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import ugettext as _
from django.views.generic.base import View

from rdrf.db.contexts_api import RDRFContextManager
from rdrf.forms.components import FormGroupButton
from rdrf.forms.progress.form_progress import FormProgress
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.helpers.utils import MinType, consent_check
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient


logger = logging.getLogger(__name__)


class PatientsListingView(View):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry_model = None
        self.user = None
        self.registries = []
        self.patient_id = None

        # grid params
        self.custom_ordering = None
        self.start = None
        self.length = None
        self.page_number = None
        self.sort_field = None
        self.sort_direction = None
        self.columns = None
        self.patients_base = None  # Queryset of patients in registry, visible for user
        self.patients = None       # Queryset of patients_base with user-supplied filters applied
        self.searchPanesOptions = None
        self.context = {}
        self.bottom = MinType()

    def get(self, request):
        # get just displays the empty table and writes the page
        # which initiates an ajax/post request on registry select
        # the protocol is the jquery DataTable
        # see http://datatables.net/manual/server-side
        self.user = request.user

        self.do_security_checks()
        self.set_csrf(request)
        self.set_registry(request)
        self.set_registries()  # for drop down
        self.patient_id = request.GET.get("patient_id", None)
        self.columns = [col.to_dict(i) for i, col in enumerate(self.get_configure_columns())]
        if not self.columns:
            raise PermissionDenied()

        template_context = self.build_context()
        template = self.get_template()

        return render(request, template, template_context)

    def get_template(self):
        if not self.registries:
            return 'rdrf_cdes/patients_listing_no_registries.html'
        return 'rdrf_cdes/patients_listing.html'

    def build_context(self):
        return {
            "registries": self.registries,
            "location": _("Patient Listing"),
            "patient_id": self.patient_id,
            "registry_code": self.registry_model.code if self.registry_model else None,
            "columns": self.columns,
        }

    def get_columns(self):
        columns = [
            ColumnFullName(_("Patient"), "patients.can_see_full_name"),
            ColumnDateOfBirth(_("Date of Birth"), "patients.can_see_dob"),
            ColumnCodeField(_("Code"), "patients.can_see_code_field"),
            ColumnWorkingGroups(_("Working Groups"), "patients.can_see_working_groups"),
            ColumnDiagnosisProgress(_("Diagnosis Entry Progress"), "patients.can_see_diagnosis_progress"),
            ColumnDiagnosisCurrency(_("Updated < 365 days"), "patients.can_see_diagnosis_currency"),
        ]

        if any(r.has_feature(RegistryFeatures.STAGES) for r in self._users_registries()):
            columns.append(ColumnPatientStage(_("Stage"), "patients.can_see_data_modules"))

        columns += [
            ColumnContextMenu(_("Modules"), "patients.can_see_data_modules"),
        ]
        return columns

    def get_configure_columns(self):
        columns = self.get_columns()
        for i, col in enumerate(columns):
            col.configure(self.registry_model, self.user, i)
        return [col for col in columns if col.user_can_see]

    def do_security_checks(self):
        if self.user.is_patient:
            raise PermissionDenied()

    def set_csrf(self, request):
        self.context.update(csrf(request))

    def set_registry(self, request):
        registry_code = request.GET.get("registry_code", None)
        if registry_code is not None:
            try:
                self.registry_model = Registry.objects.get(code=registry_code)
            except Registry.DoesNotExist:
                return HttpResponseRedirect("/")

    def _users_registries(self):
        return Registry.objects.all() if self.user.is_superuser else self.user.registry.all()

    def set_registries(self):
        if self.registry_model is None:
            self.registries = [r for r in self._users_registries()]
        else:
            self.registries = [self.registry_model]

    def json(self, data):
        json_data = json.dumps(data)
        return HttpResponse(json_data, content_type="application/json")

    def post(self, request):
        # see http://datatables.net/manual/server-side
        self.user = request.user
        if self.user and self.user.is_anonymous:
            login_url = "%s?next=%s" % (reverse("two_factor:login"), reverse("login_router"))
            return redirect(login_url)
        self.set_parameters(request)
        self.set_csrf(request)
        rows = self.get_results(request)
        results_dict = self.get_results_dict(self.draw, rows)
        return self.json(results_dict)

    def set_parameters(self, request):
        self.user = request.user
        self.registry_code = request.GET.get("registry_code")
        self.registry_model = get_object_or_404(Registry, code=self.registry_code)

        self.clinicians_have_patients = self.registry_model.has_feature(RegistryFeatures.CLINICIANS_HAVE_PATIENTS)
        self.form_progress = FormProgress(self.registry_model)
        self.supports_contexts = self.registry_model.has_feature(RegistryFeatures.CONTEXTS)
        self.rdrf_context_manager = RDRFContextManager(self.registry_model)

        def getint(param):
            try:
                return int(request.POST.get(param) or 0)
            except ValueError:
                return 0

        self.search_term = request.POST.get("search[value]") or ""
        self.draw = getint("draw")  # unknown
        self.start = getint("start")  # offset
        self.length = getint("length")  # page size
        self.page_number = ((self.start / self.length) if self.length else 0) + 1

        self.sort_field, self.sort_direction = self.get_ordering(request)

        self.columns = self.get_configure_columns()

    def get_results(self, request):
        if self.registry_model is None:
            return []
        if not self.check_security():
            return []

        patients = self.run_query()
        return patients

    def check_security(self):
        self.do_security_checks()
        if not self.user.is_superuser:
            if self.registry_model.code not in [r.code for r in self.user.registry.all()]:
                logger.info(
                    "User %s tried to browse patients in registry %s of which they are not a member" %
                    (self.user, self.registry_model.code))
                return False
        return True

    def get_ordering(self, request):
        # columns[0][data]:full_name
        # order[0][column]:1
        # order[0][dir]:asc
        sort_column_index = None
        sort_direction = None
        for key in request.POST:
            if key.startswith("order"):
                if "[column]" in key:
                    sort_column_index = request.POST[key]
                elif "[dir]" in key:
                    sort_direction = request.POST[key]

        column_name = "columns[%s][data]" % sort_column_index
        sort_field = request.POST.get(column_name, None)
        return sort_field, sort_direction

    def run_query(self):
        self.patients_base = self.filter_by_user_and_registry()
        self.apply_ordering()
        self.apply_filters()
        return self.get_rows_in_page()

    def _get_main_or_default_context(self, patient_model):
        # for registries which do not have multiple contexts this will be the single context model
        # assigned to the patient
        # for registries which allow multiple form groups, it will be the
        # (only) context with cfg marked as default
        context_model = patient_model.default_context(self.registry_model)
        assert context_model is not None, "Expected context model to exist always"
        if context_model.context_form_group:
            assert context_model.context_form_group.is_default, "Expected to always get a context of the default form group"

        return context_model

    def apply_custom_ordering(self, qs):
        key_func = [col.sort_key(self.supports_contexts, self.form_progress, self.rdrf_context_manager)
                    for col in self.columns
                    if col.field == self.sort_field and col.sort_key and not col.sort_fields]

        if key_func:
            # we have to retrieve all rows - otherwise , queryset has already been
            # ordered on base model
            k = key_func[0]

            def key_func_wrapper(thing):
                value = k(thing)
                return self.bottom if value is None else value

            return sorted(qs, key=key_func_wrapper, reverse=(self.sort_direction == "desc"))
        else:
            return qs

    def get_rows_in_page(self):
        results = self.apply_custom_ordering(self.patients)

        rows = []
        paginator = Paginator(results, self.length)
        try:
            page = paginator.page(self.page_number)
        except InvalidPage:
            logger.error("invalid page number: %s" % self.page_number)
            return []

        self.append_rows(page, rows)
        return rows

    def append_rows(self, page_object, row_list_to_update):
        if self.registry_model.has_feature(RegistryFeatures.CONSENT_CHECKS):
            row_list_to_update.extend([self._get_row_dict(obj) for obj in page_object.object_list
                                       if consent_check(self.registry_model,
                                                        self.user,
                                                        obj,
                                                        "see_patient")])
        else:
            row_list_to_update.extend([self._get_row_dict(obj)
                                       for obj in page_object.object_list])

    def _get_row_dict(self, instance):
        # we need to do this so that the progress data for this instance
        # loaded!
        self.form_progress.reset()
        self.form_progress._set_current(instance)
        return {
            col.field: col.fmt(
                col.cell(
                    instance,
                    self.supports_contexts,
                    self.form_progress,
                    self.rdrf_context_manager)) for col in self.columns}

    def apply_filters(self):
        self.patients = self.patients_base.all()
        if self.search_term:
            name_filter = Q(given_names__icontains=self.search_term) | Q(family_name__icontains=self.search_term)
            stage_filter = Q(stage__name__istartswith=self.search_term)
            self.patients = self.patients.filter(Q(name_filter | stage_filter))

    def filter_by_user_and_registry(self):
        return Patient.objects.get_by_user_and_registry(self.user, self.registry_model)

    def apply_ordering(self):
        if self.sort_field and self.sort_direction:
            def sdir(field):
                return "-" + field if self.sort_direction == "desc" else field

            sort_fields = chain(*[map(sdir, col.sort_fields)
                                  for col in self.columns
                                  if col.field == self.sort_field])

            self.patients_base = self.patients_base.order_by(*sort_fields)

    def get_results_dict(self, draw, rows):
        results = {
            "draw": draw,
            "recordsTotal": self.patients_base.count(),
            "recordsFiltered": self.patients.count(),
            "rows": rows,
        }
        if self.searchPanesOptions:
            results["searchPanes"] = {
                "options": self.searchPanesOptions
            }
        return results


class Column(object):
    field = "id"
    sort_fields = ["id"]
    bottom = MinType()
    visible = True

    def __init__(self, label, perm):
        self.label = label
        self.perm = perm

    def configure(self, registry, user, order):
        self.registry = registry
        self.user = user
        self.order = order
        self.user_can_see = user.has_perm(self.perm)

    def sort_key(self, supports_contexts=False,
                 form_progress=None, context_manager=None):

        def sort_func(patient):
            value = self.cell(patient, supports_contexts, form_progress, context_manager)
            return self.bottom if value is None else value

        return sort_func

    def cell(self, patient, supports_contexts=False,
             form_progress=None, context_manager=None):
        if "__" in self.field:
            patient_field, related_object_field = self.field.split("__")
            related_object = getattr(patient, patient_field)
            if related_object.__class__.__name__ == 'ManyRelatedManager':
                related_object = related_object.first()

            if related_object is not None:
                related_value = getattr(related_object, related_object_field)
            else:
                related_value = None
            return related_value
        return getattr(patient, self.field)

    def fmt(self, val):
        return str(val)

    def to_dict(self, i):
        "Structure used by jquery datatables"
        return {
            "data": self.field,
            "label": self.label,
            "visible": self.visible,
            "order": i,
        }


class ColumnFullName(Column):
    field = "full_name"
    sort_fields = ["family_name", "given_names"]

    def configure(self, registry, user, order):
        super(ColumnFullName, self).configure(registry, user, order)
        if not registry:
            return "<span>%d %s</span>"

        # cache reversed url because urlroute searches are slow
        base_url = reverse("patient_edit", kwargs={"registry_code": registry.code,
                                                   "patient_id": 0})
        self.link_template = '<a href="%s">%%s</a>' % (base_url.replace("/0", "/%d"))

    def cell(self, patient, supports_contexts=False, form_progress=None, context_manager=None):
        return self.link_template % (patient.id, patient.display_name)


class ColumnDateOfBirth(Column):
    field = "date_of_birth"
    sort_fields = ["date_of_birth"]

    def fmt(self, val):
        return date_format(val) if val is not None else ""


class ColumnCodeField(Column):
    field = 'code_field'
    sort_fields = []


class ColumnOptionalContext(Column):
    sort_fields = []

    def cell(self, patient, supports_contexts=False, form_progress=None, context_manager=None):
        return self.cell_optional_contexts(patient, form_progress, context_manager)

    def fmt(self, val):
        return self.icon(None) if val is None else self.fmt_optional_contexts(val)

    def cell_optional_contexts(self, patient, form_progress=None, context_manager=None):
        pass

    def fmt_optional_contexts(self, val):
        return val

    def icon(self, tick):
        icon = "check" if tick else "times"
        color = "green" if tick else "red"
        # fixme: replace inline style with css class
        return "<span class='fa fa-%s' style='color:%s'></span>" % (icon, color)


class ColumnWorkingGroups(Column):
    field = "working_groups__name"
    sort_fields = ["working_groups__name"]


class ColumnDiagnosisProgress(ColumnOptionalContext):
    field = "diagnosis_progress"

    def cell_optional_contexts(self, patient, form_progress=None, context_manager=None):
        default_ctx = context_manager.get_or_create_default_context(patient) if context_manager else None
        return form_progress.get_group_progress("diagnosis", patient, default_ctx)

    def fmt_optional_contexts(self, progress_number):
        template = "<div class='progress'><div class='progress-bar progress-bar-custom' role='progressbar'" \
                   " aria-valuenow='%s' aria-valuemin='0' aria-valuemax='100' style='width: %s%%'>" \
                   "<span class='progress-label'>%s%%</span></div></div>"
        return template % (progress_number, progress_number, progress_number)


class ColumnDiagnosisCurrency(ColumnOptionalContext):
    field = "diagnosis_currency"

    def cell_optional_contexts(self, patient, form_progress=None, context_manager=None):
        default_ctx = context_manager.get_or_create_default_context(patient) if context_manager else None
        return form_progress.get_group_currency("diagnosis", patient, default_ctx)

    def fmt_optional_contexts(self, diagnosis_currency):
        return self.icon(diagnosis_currency)


class ColumnPatientStage(Column):
    field = "stage"
    sort_fields = ["stage__id"]

    def fmt(self, val):
        if self.registry and self.registry.has_feature(RegistryFeatures.STAGES):
            return str(val)
        return "N/A"


class ColumnContextMenu(Column):
    field = "context_menu"

    def configure(self, registry, user, order):
        super(ColumnContextMenu, self).configure(registry, user, order)
        self.registry_has_context_form_groups = registry.has_groups if registry else False

        if registry:
            # fixme: slow, do intersection instead
            self.free_forms = list(filter(user.can_view, registry.free_forms))
            self.fixed_form_groups = registry.fixed_form_groups
            self.multiple_form_groups = registry.multiple_form_groups

    def cell(self, patient, supports_contexts=False, form_progress=None, context_manager=None):
        return " ".join(self._get_forms_buttons(patient))

    def _get_forms_buttons(self, patient, form_progress=None, context_manager=None):
        if not self.registry_has_context_form_groups:
            # if there are no context groups -normal registry
            return [self._get_forms_button(patient, None, self.free_forms)]
        else:
            # display one button per form group
            buttons = []
            for fixed_form_group in self.fixed_form_groups:
                buttons.append(self._get_forms_button(patient,
                                                      fixed_form_group,
                                                      fixed_form_group.forms))

            for multiple_form_group in self.multiple_form_groups:
                buttons.append(self._get_forms_button(patient,
                                                      multiple_form_group,
                                                      multiple_form_group.forms))
            return buttons

    def _get_forms_button(self, patient_model, context_form_group, forms):
        button = FormGroupButton(self.registry, self.user, patient_model, context_form_group)
        return button.html

    def sort_key(self, *args, **kwargs):
        return None


class DynamicPatientListingView(PatientsListingView):
    COLUMN_FUNCS = []

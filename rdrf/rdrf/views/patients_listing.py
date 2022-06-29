import json
import logging
from itertools import chain

from django.core.exceptions import PermissionDenied
from django.core.paginator import InvalidPage, Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.context_processors import csrf
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views.generic.base import View

from rdrf.db.contexts_api import RDRFContextManager
from rdrf.forms.progress.form_progress import FormProgress
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.helpers.utils import MinType, consent_check
from rdrf.models.definition.models import Registry
from rdrf.patients.patient_list_configuration import PatientListConfiguration
from rdrf.patients.query_data import PatientQueryData
from registry.patients.models import Patient
from report.schema import FacetType

logger = logging.getLogger(__name__)


class PatientsListsView(View):
    def get(self, request):
        registries = Registry.objects.filter_by_user(request.user)

        if len(registries) == 1:
            return redirect(reverse('patient_list', args=[registries.first().code]))

        context = {'registries': registries}
        return render(request, 'rdrf_cdes/patients_listing_all.html', context)


class PatientsListingView(View):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry_model = None
        self.user = None

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
        self.context = {}
        self.bottom = MinType()

        # Filters
        self.facets = None
        self.selected_filters = None

    def _user_facets(self, registry_facets):
        patient_query = PatientQueryData(self.registry_model)
        facet_values = patient_query.get_facet_values(self.request, registry_facets.keys())
        facet_types_dict = {facet_type.field: facet_type for facet_type in [FacetType(**value) for value in facet_values]}

        user_facets = {}
        for key, facet_config in registry_facets.items():
            facet_type = facet_types_dict.get(key)
            facet_permission = facet_config.get('permission')
            if facet_type and (not facet_permission or self.user.has_perm(facet_permission)):
                user_facets[key] = {**facet_config, **{'categories': facet_type.categories}}

        return user_facets

    def get(self, request, registry_code):
        # get just displays the empty table and writes the page
        # which initiates an ajax/post request on registry select
        # the protocol is the jquery DataTable
        # see http://datatables.net/manual/server-side
        self.user = request.user

        self.do_security_checks()
        self.set_csrf(request)
        self.registry_model = get_object_or_404(Registry, code=registry_code)

        self.columns, self.facets = self.get_user_table_config()

        if not self.columns:
            raise PermissionDenied()

        template_context = self.build_context()
        template = self.get_template()

        return render(request, template, template_context)

    def get_template(self):
        return 'rdrf_cdes/patients_listing.html'

    def build_context(self):
        return {
            "location": _("Patient Listing"),
            "registry": self.registry_model,
            "columns": [column.to_dict(i) for i, column in enumerate(self.columns)],
            "facets": self.facets
        }

    def get_user_table_config(self):
        registry_config = PatientListConfiguration(self.registry_model)
        registry_columns = registry_config.get_columns()
        registry_facets = registry_config.get_facets()

        # initialise data table columns
        for i, (column_key, datatable_column) in enumerate(registry_columns.items()):
            datatable_column.configure(self.registry_model, self.user, i)

        user_columns = [value for key, value in registry_columns.items() if value.user_can_see]

        # initialise filters
        user_facets = self._user_facets(registry_facets)

        return user_columns, user_facets

    def do_security_checks(self):
        if self.user.is_patient:
            raise PermissionDenied()

    def set_csrf(self, request):
        self.context.update(csrf(request))

    def json(self, data):
        json_data = json.dumps(data)
        return HttpResponse(json_data, content_type="application/json")

    def post(self, request, registry_code):
        # see http://datatables.net/manual/server-side
        self.user = request.user
        if self.user and self.user.is_anonymous:
            login_url = "%s?next=%s" % (reverse("two_factor:login"), reverse("login_router"))
            return redirect(login_url)
        self._set_data_parameters(request, registry_code)
        self.set_csrf(request)
        rows = self.get_results(request)
        results_dict = self.get_results_dict(self.draw, rows)
        return self.json(results_dict)

    def _set_data_parameters(self, request, registry_code):
        self.user = request.user
        self.registry_model = get_object_or_404(Registry, code=registry_code)

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

        self.columns, self.facets = self.get_user_table_config()
        self.selected_filters = self._get_request_filters(request, self.facets)

    def _get_request_filters(self, request, facets):
        filters = {}  # e.g. {'living_status': 'Alive'}
        for key, val in facets.items():
            valid_options = [option.get('value') for option in val.get('categories')]
            selected_filter_values = [value if value != "None" else None
                                      for value in request.POST.getlist(f'filter[{key}][]')]

            valid_filter_values = [value for value in selected_filter_values if value in valid_options]
            if valid_filter_values:
                filters[key] = valid_filter_values
        return filters

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

        if self.selected_filters:
            patient_filters = []
            for field, filter_values in self.selected_filters.items():
                field_filter = {f'{field}__in': [value for value in filter_values if value is not None]}
                if None in filter_values:
                    patient_filters.append(Q(**field_filter) | Q(**{f'{field}__isnull': True}))
                else:
                    patient_filters.append(Q(**field_filter))

            self.patients = self.patients.filter(*patient_filters)

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
            "rows": rows
        }
        return results

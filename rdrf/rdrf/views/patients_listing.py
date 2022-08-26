import json
import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.context_processors import csrf
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views.generic.base import View

from rdrf.db.contexts_api import RDRFContextManager
from rdrf.forms.progress.form_progress import FormProgress
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry
from rdrf.patients.patient_list_configuration import PatientListConfiguration
from rdrf.patients.query_data import query_patient_facets, build_patients_query, \
    build_patient_filters, build_all_patients_query, get_all_patients, build_search_item
from registry.patients.models import Patient
from report.schema import create_dynamic_schema, to_camel_case

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
        self.start = None
        self.length = None
        self.sort_field = None
        self.sort_direction = None
        self.columns = None
        self.context = {}

        # Filters
        self.facets = None
        self.selected_filters = None

    def _user_facets(self, request, registry_facets):
        facets = query_patient_facets(request, self.registry_model, registry_facets.keys())

        user_facets = {}
        for key, facet_config in registry_facets.items():
            facet = facets.get(key)
            facet_permission = facet_config.get('permission')
            if facet and (not facet_permission or self.user.has_perm(facet_permission)):
                user_facets[key] = {**facet_config, **{'categories': facet}}

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

        self.columns, self.facets = self._get_user_table_config(request)

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

    def _get_user_table_config(self, request):
        registry_config = PatientListConfiguration(self.registry_model)
        registry_columns = registry_config.get_columns()
        registry_facets = registry_config.get_facets()

        # initialise data table columns
        for i, (column_key, datatable_column) in enumerate(registry_columns.items()):
            datatable_column.configure(self.registry_model, self.user, i)

        user_columns = [value for key, value in registry_columns.items() if value.user_can_see]

        # initialise filters
        user_facets = self._user_facets(request, registry_facets)

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
        base_total, filtered_total, rows = self._get_results(request)
        results_dict = self._get_results_dict(self.draw, base_total, filtered_total, rows)
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
        self.draw = getint("draw")  # number of times the results have been drawn
        self.start = getint("start")  # offset
        self.length = getint("length")  # page size

        self.sort_field, self.sort_direction = self._get_ordering(request)

        self.columns, self.facets = self._get_user_table_config(request)
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

    def _sort_fields(self):
        if self.sort_field and self.sort_direction:
            def sort_field_with_direction(field):
                return "-" + field if self.sort_direction == "desc" else field

            return [sort_field_with_direction(sort_field)
                    for col in self.columns
                    for sort_field in col.sort_fields
                    if col.field == self.sort_field]

    def _query_all_patients(self, request, registry, filters, patient_fields, sort_fields, pagination):
        patient_query = build_patients_query(patient_fields, sort_fields, pagination)

        operation_input, query_input, variables = build_patient_filters(filters)
        all_patients_query = build_all_patients_query(registry, ['total', patient_query], query_input, operation_input)

        schema = create_dynamic_schema()

        result_all = schema.execute(build_all_patients_query(registry, ['total']), context_value=request)
        result_filtered = schema.execute(all_patients_query, variable_values=variables, context_value=request)

        return get_all_patients(result_all, registry).get('total'), get_all_patients(result_filtered, registry)

    def _get_results(self, request):
        if self.registry_model is None:
            return []
        if not self._check_security():
            return []

        filters = {**self.selected_filters}

        if self.search_term:
            patient_search = build_search_item(self.search_term, ['givenNames', 'familyName', 'stage'])
            filters.update({'search': [patient_search]})

        patient_fields = ['id']
        sort_fields = self._sort_fields()
        schema_sort_fields = list(map(to_camel_case, sort_fields))
        pagination = {'offset': self.start, 'limit': self.length}

        base_total, results = self._query_all_patients(request,
                                                       self.registry_model,
                                                       filters,
                                                       patient_fields,
                                                       schema_sort_fields,
                                                       pagination)

        patient_ids = [patient['id'] for patient in results.get('patients', [])]
        patients = Patient.objects.filter(id__in=patient_ids).order_by(*sort_fields)

        filtered_total = results.get('total')
        patients_dict = [self._get_row_dict(patient) for patient in patients]

        return base_total, filtered_total, patients_dict

    def _check_security(self):
        self.do_security_checks()
        if not self.user.is_superuser:
            if self.registry_model.code not in [r.code for r in self.user.registry.all()]:
                logger.info(
                    "User %s tried to browse patients in registry %s of which they are not a member" %
                    (self.user, self.registry_model.code))
                return False
        return True

    def _get_ordering(self, request):
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

    def _get_results_dict(self, draw, base_total, filtered_total, rows):
        results = {
            "draw": draw,
            "recordsTotal": base_total,
            "recordsFiltered": filtered_total,
            "rows": rows
        }
        return results

import json
import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic.base import View

from explorer.models import Query
from rdrf.security.mixins import ReportAccessMixin
from rdrf.services.io.reporting.reporting_table import ReportTable

logger = logging.getLogger(__name__)


class ReportView(ReportAccessMixin, View):

    def get(self, request):
        user = request.user
        context = {}
        context['reports'] = Query.objects.reports_for_user(user)
        context["location"] = 'Reports'
        return render(request, 'rdrf_cdes/reports.html', context)


class ReportDataTableView(ReportAccessMixin, View):

    def get(self, request, query_model_id):
        user = request.user
        query_model = get_object_or_404(Query, pk=query_model_id)

        self._permission_check(query_model, user)

        report_table = ReportTable(user, query_model)
        registry_model = query_model.registry

        return render(request, 'rdrf_cdes/report_table_view.html', {
            "location": report_table.title,
            "registry_code": registry_model.code,
            "max_items": query_model.max_items,
            "columns": report_table.columns,
            "report_title": query_model.title,
            "api_url": reverse('report_datatable', args=[query_model_id]),
        })

    def _permission_check(self, query_model, user):
        if not Query.objects.reports_for_user(user).filter(pk=query_model.id).exists():
            raise PermissionDenied

    def post(self, request, query_model_id):
        user = request.user
        query_model = get_object_or_404(Query, pk=query_model_id)

        self._permission_check(query_model, user)

        query_parameters = self._get_query_parameters(request)
        report_table = ReportTable(user, query_model)

        rows = report_table.run_query(query_parameters)

        try:
            results_dict = self._build_result_dict(rows)
            return self._json(results_dict)
        except Exception as ex:
            logger.error("Could not jsonify results: %s" % ex)
            return self._json({})

    def _json(self, result_dict):
        json_data = json.dumps(result_dict)

        if self._validate_json(json_data):
            return HttpResponse(json_data, content_type="application/json")
        else:
            return HttpResponse(json.dumps(self._build_result_dict([])),
                                content_type="application/json")

    def _validate_json(self, json_data):
        try:
            json.loads(json_data)
        except ValueError:
            return False
        return True

    def _build_result_dict(self, rows):
        return {
            "recordsTotal": len(rows),
            "recordsFiltered": 0,
            "rows": rows,
        }

    def _get_query_parameters(self, request):
        p = {}
        p["search"] = request.POST.get("search[value]", None)
        p["search_regex"] = request.POST.get("search[regex]", False)
        sort_field, sort_direction = self._get_ordering(request)
        p["sort_field"] = sort_field
        p["sort_direction"] = sort_direction
        p["start"] = request.POST.get("start", 0)
        p["length"] = request.POST.get("length", 10)
        return p

    def _get_ordering(self, request):
        # columns[0][data]:full_name
        # ...
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

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from explorer.models import Query
from rdrf.services.io.reporting.reporting_table import ReportTable

logger = logging.getLogger(__name__)


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class ReportView(LoginRequiredMixin, View):

    def get(self, request):
        user = request.user

        reports = None

        if user.is_superuser:
            reports = Query.objects.all()
        elif user.is_curator or (user.is_clinician and user.ethically_cleared):
            reports = Query.objects.filter(
                registry__in=[
                    reg.id for reg in user.get_registries()]).filter(
                access_group__in=[
                    g.id for g in user.get_groups()]).distinct()

        context = {}
        context['reports'] = reports
        context["location"] = 'Reports'
        return render(request, 'rdrf_cdes/reports.html', context)


class ReportDataTableView(LoginRequiredMixin, View):

    def get(self, request, query_model_id):
        user = request.user
        try:
            query_model = Query.objects.get(pk=query_model_id)
        except Query.DoesNotExist:
            raise Http404("Report %s does not exist" % query_model_id)

        if not self._sanity_check(query_model, user):
            return HttpResponseRedirect("/")

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

    def _sanity_check(self, query_model, user):
        # todo sanity check
        return True

    def post(self, request, query_model_id):
        user = request.user
        try:
            query_model = Query.objects.get(pk=query_model_id)
        except Query.DoesNotExist:
            raise Http404("Report %s does not exist" % query_model_id)

        if not self._sanity_check(query_model, user):
            return HttpResponseRedirect("/")

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

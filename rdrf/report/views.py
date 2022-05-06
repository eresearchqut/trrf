import logging

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import StreamingHttpResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View

from rdrf.models.definition.models import ContextFormGroup, Registry
from rdrf.security.mixins import SuperuserRequiredMixin
from report.forms import ReportDesignerForm
from report.models import ReportDesign
from report.report_builder import ReportBuilder

logger = logging.getLogger(__name__)


class ReportsAccessCheckMixin:
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_curator or request.user.is_clinician):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ReportDownloadAccessCheckMixin:
    def dispatch(self, request, *args, **kwargs):
        if not ReportDesign.objects.reports_for_user(request.user).filter(pk=kwargs['report_id']).exists():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ReportsView(ReportsAccessCheckMixin, View):
    def get(self, request):
        return render(request, 'reports_list.html', {
            'reports': ReportDesign.objects.reports_for_user(request.user)
        })


class ReportDownloadView(ReportDownloadAccessCheckMixin, View):
    def get(self, request, report_id, format):
        report_design = get_object_or_404(ReportDesign, pk=report_id)
        report = ReportBuilder(report_design=report_design)

        is_valid, errors = report.validate_query(request)
        if not is_valid:
            logger.error(errors)
            return render(request, 'report_download_errors.html', {'errors': errors})

        if format == 'csv':
            is_valid, errors = report.validate_for_csv_export()
            if not is_valid:
                return render(request, 'report_download_errors.html', {'errors': errors})
            content_type = 'text/csv; charset=utf-8'
            content = report.export_to_csv(request)
        elif format == 'json':
            # Line delimited json to support streaming of data
            content_type = 'application/json-seq'
            content = report.export_to_json(request)
        else:
            raise Exception("Unsupported download format")

        filename = f"report_{report_design.title}.{format}"
        response = StreamingHttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ReportDesignView(SuperuserRequiredMixin, View):
    def get(self, request, report_id=None):
        if report_id:
            report = get_object_or_404(ReportDesign, id=report_id)
            report_design_form = ReportDesignerForm(instance=report)
            report_design_form.setup_initials()
        else:
            report_design_form = ReportDesignerForm()

        params = _get_default_params(request, report_design_form)
        params.update({'registry__cfgs': {registry: ContextFormGroup.objects.filter(registry=registry).order_by('sort_order', 'code')
                                          for registry in Registry.objects.all()}
                       })
        return render(request, 'report_designer.html', params)

    def post(self, request, report_id=None):
        if report_id:
            report = get_object_or_404(ReportDesign, id=report_id)
            form = ReportDesignerForm(request.POST, instance=report)
        else:
            form = ReportDesignerForm(request.POST)

        if form.is_valid():
            form.save_to_model()
            messages.success(request, f'Report "{form.instance.title}" has been saved successfully.')
            return redirect('report:reports_list')
        else:
            return render(request, 'report_designer.html', _get_default_params(request, form))

    def delete(self, request, report_id):
        report = get_object_or_404(ReportDesign, id=report_id)
        report.delete()
        return HttpResponse(status=204)


def _get_default_params(request, form):
    return {
        'form': form
    }

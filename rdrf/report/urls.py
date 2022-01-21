from django.urls import re_path

from report.views import ReportDesignView, ReportDeleteView, ReportDownloadView, ReportsView

app_name = 'rdrf'

urlpatterns = [

    re_path(r'^report$', ReportDesignView.as_view(), name='report_designer'),
    re_path(r'^report/(?P<report_id>\w+)/?$', ReportDesignView.as_view(), name='report_designer'),
    re_path(r'^report/(?P<report_id>\w+)/delete/?$', ReportDeleteView.as_view(), name='report_delete'),
    re_path(r'^report/download/(?P<report_id>\w+)/(?P<format>\w+)/?$', ReportDownloadView.as_view(),
            name='report_download'),
    re_path(r'^reports$', ReportsView.as_view(), name='reports_list'),

]

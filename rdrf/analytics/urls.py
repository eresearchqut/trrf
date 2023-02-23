from django.urls import re_path

from analytics.views import AnalyticsView, AnalyticsDataView, AnalyticsChartView, AnalyticsTableView, \
    AnalyticsTableDataView, ExportAnalyticsView, AnalyticsChartDesignView

app_name = 'analytics'

urlpatterns = [
    re_path(r'^table/?$', AnalyticsTableView.as_view(), name='datatable_view'),
    re_path(r'^data/?$', AnalyticsTableDataView.as_view(), name='datatable_data'),
    re_path(r'^export/?$', ExportAnalyticsView.as_view(), name='export'),
    re_path(r'^chart_design/?$', AnalyticsChartDesignView.as_view(), name='chart_designer'),
    re_path(r'^configure$', AnalyticsView.as_view(), name='analytics_configure'),
    re_path(r'^cde_data/(?P<form_name>\w+)/(?P<section_code>\w+)/(?P<cde_code>\w+)/?$', AnalyticsDataView.as_view(), name='analytics_data'),
    re_path(r'^chart/(?P<form_name>\w+)/(?P<section_code>\w+)/(?P<cde_code>\w+)/?$', AnalyticsChartView.as_view(), name='analytics_chart')
]

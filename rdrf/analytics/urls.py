from django.urls import re_path

from analytics.views import AnalyticsView, AnalyticsDataView, AnalyticsChartView

app_name = 'analytics'

urlpatterns = [
    re_path(r'^configure$', AnalyticsView.as_view(), name='analytics_configure'),
    re_path(r'^data/(?P<form_name>\w+)/(?P<section_code>\w+)/(?P<cde_code>\w+)/?$', AnalyticsDataView.as_view(), name='analytics_data'),
    re_path(r'^chart/(?P<form_name>\w+)/(?P<section_code>\w+)/(?P<cde_code>\w+)/?$', AnalyticsChartView.as_view(), name='analytics_chart')
]

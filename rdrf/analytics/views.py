import json
import logging
import random

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from analytics.models import ClinicalDataView
from rdrf.models.definition.models import CommonDataElement
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


class AnalyticsView(View):

    def reportable_cdes(self):
        # TODO filter based on CDE type (e.g. can't report on free text fields)
        return ClinicalDataView.objects\
            .exclude(cde_value__exact='')\
            .exclude(cde_value__exact='null')\
            .exclude(cde_value__isnull=True)\
            .values('form_name', 'section_code', 'cde_code')\
            .annotate(cnt_value=Count('cde_value'))\
            .order_by('form_name', 'section_code', 'cde_code')

    def get(self, request):
        params = {
            'reportable_cdes': self.reportable_cdes()
        }
        return render(request, 'analytics.html', params)


class BaseAnalyticsView(View):

    def get_cde(self, cde_code):
        return CommonDataElement.objects.get(code=cde_code)

    def get_data(self, form_name, section_code, cde_code):
        return ClinicalDataView.objects\
            .exclude(cde_value__exact='')\
            .exclude(cde_value__exact='null')\
            .exclude(cde_value__isnull=True)\
            .filter(form_name=form_name, section_code=section_code, cde_code=cde_code)\
            .values()

    def _random_colour(self):
        return random.choices(range(256), k=3)

    def _parse_isoduration(self, duration):
        ## https://stackoverflow.com/a/74557888
        def get_isosplit(duration, split):
            logger.info(duration)
            logger.info(split)
            if split in duration:
                n, duration = duration.split(split, 1)
            else:
                n = '0'
            return n.replace(',', '.'), duration  # to handle like "P0,5Y"

        logger.info(f'duration={duration}')
        duration = duration.split('P', 1)[-1]  # Remove prefix
        s_yr, duration = get_isosplit(duration, 'Y')  # Step through letter dividers
        s_mo, duration = get_isosplit(duration, 'M')
        s_wk, duration = get_isosplit(duration, 'W')
        s_dy, duration = get_isosplit(duration, 'D')
        _, duration = get_isosplit(duration, 'T')
        s_hr, duration = get_isosplit(duration, 'H')
        s_mi, duration = get_isosplit(duration, 'M')
        s_sc, duration = get_isosplit(duration, 'S')
        n_yr = float(s_yr) * 365  # approx days for year, month, week
        n_mo = float(s_mo) * 30.4
        n_wk = float(s_wk) * 7
        import datetime
        dt = datetime.timedelta(days=n_yr + n_mo + n_wk + float(s_dy), hours=float(s_hr), minutes=float(s_mi),
                                seconds=float(s_sc))
        return int(dt.total_seconds() * 1000)  ## int(dt.total_seconds()) | dt

    def get_chart_data(self, form_name, section_code, cde_code, demographic_filter=None):
        labels = []
        chart_type = 'bar'

        cde_model = self.get_cde(cde_code)

        datasets = []

        if demographic_filter:
            demographic_categories = Patient.objects.all().order_by(demographic_filter).values(demographic_filter).distinct(demographic_filter)
            for category in demographic_categories:
                graph_colour = self._random_colour()
                patients = Patient.objects.filter(**category)
                cat_data = self.get_data(form_name, section_code, cde_code)
                patient_ids = list(patients.values_list('id', flat=True))
                cdf = cat_data.filter(patient_id__in=patient_ids)
                label = category.get(demographic_filter)
                value_by_ranges = cdf.values('cde_value').annotate(cnt=Count('cde_value'))
                chart_dataset = [{'x': result.get('cde_value'), 'y': result.get('cnt')} for result in value_by_ranges]
                datasets.append({
                    'label': label,
                    'data': chart_dataset,
                    'backgroundColor': f'rgb({graph_colour[0]}, {graph_colour[1]}, {graph_colour[2]})'
                })
        else:
            data_qs = self.get_data(form_name, section_code, cde_code)
            value_by_ranges = data_qs.values('cde_value').annotate(cnt=Count('cde_value'))
            dataset_data = [{'x': result.get('cde_value'), 'y': result.get('cnt')} for result in value_by_ranges]

            datasets.append({
                'label': cde_model.abbreviated_name,
                'data': dataset_data
            })

        if cde_model.datatype == 'range':
            labels = cde_model.get_range_members()

        if cde_model.datatype == 'duration':
            logger.info('unpack the duration into a timedelta')
            durations = [data.get('x')
                         for dataset in datasets
                         for data in dataset.get('data')]

            for duration in durations:
                logger.info(f'duration: {duration}')
                parsed_duration = self._parse_isoduration(duration)
                logger.info(f'parsed duration: {parsed_duration}')
            logger.info(durations)
            # import pandas as pd
            # dt = pd.Timedelta()

        return {
            'cde_name': cde_model.name,
            'datatype': cde_model.datatype,
            # 'data': list(data_qs),
            'chart': {
                'labels': labels,
                'type': chart_type,
                'datasets': datasets
            }
        }

class AnalyticsDataView(BaseAnalyticsView):

    def get(self, request, form_name, section_code, cde_code):
        return JsonResponse(self.get_chart_data(form_name, section_code, cde_code))


class AnalyticsChartView(BaseAnalyticsView):
    def get(self, request, form_name, section_code, cde_code):

        demographic_filter = request.GET.get('series')

        chart_data = self.get_chart_data(form_name, section_code, cde_code, demographic_filter)

        return render(request, 'chart.html', chart_data)


class AnalyticsTableView(View):
    def get(self, request):
        return render(request, 'table.html')


# util, move somewhere else
def getint(str_input):
    return int(str_input or 0)


class AnalyticsTableDataView(View):
    def post(self, request):
        draw = getint(request.POST.get('draw'))
        start = getint(request.POST.get('start'))
        length = getint(request.POST.get('length'))
        # columns = request.POST.getlist('columns')
        # order = request.POST.getlist('order')
        search_value = request.POST.get('search[value]')
        search_regex = request.POST.get('search[regex]')

        logger.info(f'draw={draw}')
        logger.info(f'start={start}')
        logger.info(f'length={length}')
        logger.info(f'search_value={search_value}')
        logger.info(f'search_regex={search_regex}')

        # Get records with appropriate pagination
        offset = start
        limit = length + offset
        all_data = ClinicalDataView.objects.all()
        paginated_data = all_data[offset:limit]

        return JsonResponse({
            "draw": draw,
            "recordsTotal": all_data.count(),
            "recordsFiltered": all_data.count(),
            "data": [{'form_name': data.form_name,
                      'form_entry_num': data.form_entry_num,
                      'section_code': data.section_code,
                      'cde_code': data.cde_code,
                      'cde_entry_num': data.cde_entry_num,
                      'cde_value': data.cde_value} for data in paginated_data]
        })


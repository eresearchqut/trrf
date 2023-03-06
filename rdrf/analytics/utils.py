import logging
import random

from django.db.models import Count

from analytics.forms import DATASOURCE_CDE, DATASOURCE_DEMOGRAPHIC
from analytics.models import ClinicalDataView
from registry.patients.models import Patient


logger = logging.getLogger(__name__)


def get_data(form_name, section_code, cde_code):
    return ClinicalDataView.objects\
        .filter_non_empty()\
        .filter(form_name=form_name, section_code=section_code, cde_code=cde_code)\
        .values()


def get_cde_labels(cde_model):
    if cde_model.datatype == 'range':
        return cde_model.get_range_members()


def random_colour():
    return random.choices(range(256), k=3)

def get_cde_chart_data(dataset_definition):
    form_model, section_model, cde_model = [dataset_definition.get(key) for key in ['form', 'section', 'cde']]
    data = get_data(form_model.name, section_model.code, cde_model.code)

    cde_value_counts = data.values('cde_value').annotate(cnt=Count('cde_value'))

    dataset_data = [{'x': result.get('cde_value'), 'y': result.get('cnt')} for result in cde_value_counts]

    chart_labels = get_cde_labels(cde_model)

    chart_definition = {
        'labels': chart_labels,
        'data': data,
        'source_field': 'cde_value',
        'dataset': {'label': cde_model.abbreviated_name, 'data': dataset_data}
    }

    return chart_definition


def get_demographic_values(field):
    data = Patient.objects.all()
    all_values = data.order_by(field).values(field)
    unique_values = all_values.distinct(field)

    return data, all_values, unique_values

def get_demographic_chart_data(dataset_definition):
    field = dataset_definition.get('demographic')
    # data = Patient.objects.all()
    # all_values = data.order_by(field).values(field)
    # unique_values = all_values.distinct(field)
    data, all_values, unique_values = get_demographic_values(field)

    chart_labels = [label for label in list(unique_values.values_list(field, flat=True)) if label]

    value_counts = all_values.annotate(cnt=Count(field))
    dataset_data = [{'x': result.get(field) or 'na', 'y': result.get('cnt')} for result in
                    value_counts]

    chart_definition = {
        'labels': chart_labels,
        'data': data,
        'source_field': field,
        'dataset': {'label': field, 'data': dataset_data}
    }

    return chart_definition


def get_secondary_cde_chart_data(dataset_definition, primary_chart_data):
    logger.info('TODO')
    return {}


def get_secondary_demographic_chart_data(dataset_definition, primary_chart_data):
    field = dataset_definition.get('demographic')
    data, all_values, unique_values = get_demographic_values(field)
    primary_data = primary_chart_data.get('data')
    primary_source_field = primary_chart_data.get('source_field')

    datasets = []
    for value in unique_values:
        background_colour = random_colour()
        label = value.get(field)

        category_patient_ids = list(Patient.objects.filter(**value).values_list('id', flat=True))
        category_data = primary_data.filter(patient_id__in=category_patient_ids)
        value_counts = category_data.values(primary_source_field).annotate(cnt=Count(primary_source_field))
        dataset_data = [{'x': result.get('cde_value'), 'y': result.get('cnt')} for result in value_counts]

        datasets.append({'label': label,
                         'data': dataset_data,
                         'backgroundColor': f'rgb({background_colour[0]}, {background_colour[1]}, {background_colour[2]})'
                         })

    return datasets


def get_dataset_func(dataset_functions, dataset_definition, *args):
    dataset_type = dataset_definition.get('type')
    return dataset_functions.get(dataset_type)(dataset_definition, *args)


def get_primary_chart_data(dataset_definition):
    primary_data_functions = {
        DATASOURCE_CDE: get_cde_chart_data,
        DATASOURCE_DEMOGRAPHIC: get_demographic_chart_data
    }

    return get_dataset_func(primary_data_functions, dataset_definition)


def get_secondary_chart_data(dataset_definition, primary_chart_data):
    secondary_data_functions = {
        DATASOURCE_CDE: get_secondary_cde_chart_data,
        DATASOURCE_DEMOGRAPHIC: get_secondary_demographic_chart_data
    }

    return get_dataset_func(secondary_data_functions, dataset_definition, primary_chart_data)


def get_chartjs_data_v2(chart_design):
    chart_type = chart_design.get('type')
    dataset_definitions = chart_design.get('datasets', [])
    num_definitions = len(dataset_definitions)
    assert num_definitions > 0, "Invalid chart design - no dataset definitions defined"

    primary_chart_data = get_primary_chart_data(dataset_definitions[0])

    datasets = []
    if num_definitions > 1:
        for dataset_definition in dataset_definitions[1:]:
            dataset = get_secondary_chart_data(dataset_definition, primary_chart_data)
            datasets.extend(dataset)
    else:
        datasets.append(primary_chart_data.get('dataset'))

    return {
        'chart': {
            'labels': primary_chart_data.get('labels'),
            'type': chart_type,
            'datasets': datasets
        }
    }


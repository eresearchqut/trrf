import logging
import random

from django.db.models import Count, F

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
        return {m: m for m in cde_model.get_range_members()}


def random_background_colour():
    random_colour = random.choices(range(256), k=3)
    return f'rgb({random_colour[0]}, {random_colour[1]}, {random_colour[2]})'


def get_demographic_labels(field, unique_values):
    if field == 'sex':
        return {val: dict(Patient.SEX_CHOICES).get(val)
                for val_dict in unique_values
                for val in val_dict.values()}

    # Default case
    return {val: val
            for val_dict in unique_values
            for val in val_dict.values()}


def get_demographic_values(field):
    data = Patient.objects.all().annotate(patient_id=F('id'))

    all_values = data.order_by(field).values(field)
    unique_values = all_values.distinct(field)
    labels = get_demographic_labels(field, unique_values)

    return data, all_values, unique_values, labels


def get_primary_cde_chart_data(dataset_definition):
    chart_type = dataset_definition.get('chart_type')
    form_model, section_model, cde_model = [dataset_definition.get(key) for key in ['form', 'section', 'cde']]
    data = get_data(form_model.name, section_model.code, cde_model.code)

    cde_value_counts = data.values('cde_value').annotate(cnt=Count('cde_value'))

    dataset_data = [{'x': result.get('cde_value'), 'y': result.get('cnt')} for result in cde_value_counts]

    chart_labels = get_cde_labels(cde_model)

    chart_definition = {
        'labels': chart_labels,
        'data': data,
        'source_field': 'cde_value',
        'chart_type': chart_type,
        'dataset': {'label': cde_model.abbreviated_name, 'data': dataset_data}
    }

    return chart_definition


def get_secondary_dataset(primary_chart_data, data, category_filter):
    primary_data = primary_chart_data.get('data')
    primary_labels = primary_chart_data.get('labels')
    primary_source_field = primary_chart_data.get('source_field')

    category_patient_ids = list(data.filter(**category_filter).values_list('patient_id', flat=True))
    category_data = primary_data.filter(patient_id__in=category_patient_ids)
    value_counts = category_data.order_by(primary_source_field).values(primary_source_field).annotate(cnt=Count('patient_id'))
    dataset_data = [{'x': primary_labels.get(result.get(primary_source_field)), 'y': result.get('cnt')} for result in value_counts]
    return dataset_data


def get_secondary_cde_chart_data(dataset_definition, primary_chart_data):
    chart_type = dataset_definition.get('chart_type')
    form_model, section_model, cde_model = [dataset_definition.get(key) for key in ['form', 'section', 'cde']]

    data = get_data(form_model.name, section_model.code, cde_model.code)

    cde_values = get_cde_labels(cde_model)

    return [{'label': value,
             'data': get_secondary_dataset(primary_chart_data, data, {'cde_value': value}),
             'type': chart_type,
             'backgroundColor': random_background_colour()
             } for value in cde_values]


def get_primary_demographic_chart_data(dataset_definition):
    field = dataset_definition.get('demographic')
    chart_type = dataset_definition.get('chart_type')
    data, all_values, unique_values, labels = get_demographic_values(field)

    value_counts = all_values.annotate(cnt=Count(field))
    dataset_data = [{'x': labels.get(result.get(field)) or 'na', 'y': result.get('cnt')} for result in
                    value_counts]

    chart_definition = {
        'labels': labels,
        'data': data.annotate(patient_id=F('id')),
        'source_field': field,
        'chart_type': chart_type,
        'dataset': {'label': field, 'data': dataset_data}
    }

    return chart_definition


def get_secondary_demographic_chart_data(dataset_definition, primary_chart_data):
    chart_type = dataset_definition.get('chart_type')

    field = dataset_definition.get('demographic')
    data, all_values, unique_values, labels = get_demographic_values(field)

    return [{'label': labels.get(value.get(field)),
             'data': get_secondary_dataset(primary_chart_data, data, value),
             'backgroundColor': random_background_colour(),
             'type': chart_type
             } for value in unique_values]


def get_dataset_func(dataset_functions, dataset_definition, *args):
    dataset_type = dataset_definition.get('type')
    return dataset_functions.get(dataset_type)(dataset_definition, *args)


def get_primary_chart_data(dataset_definition):
    primary_data_functions = {
        DATASOURCE_CDE: get_primary_cde_chart_data,
        DATASOURCE_DEMOGRAPHIC: get_primary_demographic_chart_data
    }

    return get_dataset_func(primary_data_functions, dataset_definition)


def get_secondary_chart_data(dataset_definition, primary_chart_data):
    secondary_data_functions = {
        DATASOURCE_CDE: get_secondary_cde_chart_data,
        DATASOURCE_DEMOGRAPHIC: get_secondary_demographic_chart_data
    }

    return get_dataset_func(secondary_data_functions, dataset_definition, primary_chart_data)


def get_chartjs_data(chart_design):
    dataset_definitions = chart_design.get('datasets', [])
    num_definitions = len(dataset_definitions)
    assert num_definitions > 0, "Invalid chart design - no dataset definitions defined"

    primary_chart_data = get_primary_chart_data(dataset_definitions[0])

    datasets = []
    if num_definitions > 1:
        datasets.append(primary_chart_data.get('dataset'))
        for dataset_definition in dataset_definitions[1:]:
            dataset = get_secondary_chart_data(dataset_definition, primary_chart_data)
            datasets.extend(dataset)
    else:
        datasets.append(primary_chart_data.get('dataset'))

    return {
        'chart': {
            'labels': list(primary_chart_data.get('labels').values()),
            'type': primary_chart_data.get('chart_type'),
            'title': chart_design.get('title'),
            'datasets': datasets
        }
    }


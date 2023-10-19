import re
from importlib import import_module

from django.conf import settings


def load_report_configuration():
    report_config_module = import_module(settings.REPORT_CONFIG_MODULE)
    get_report_config_func = getattr(report_config_module, settings.REPORT_CONFIG_METHOD_GET)
    return get_report_config_func()


def get_flattened_json_path(field):
    def resolve_nested_fields(wip_field):
        if re.search('[{}]', wip_field):
            # 2. Replace curly brace with a single underscore to separate the parts = addressType_type
            # --> regex group 1 = addressType
            # --> regex group 2 = {type}
            # --> regex group 3 = type
            wip_field = re.sub(r"(.+)({(.*)})", r"\1_\3", wip_field)

            # Keep going until we have resolved all the nested curly braces
            return resolve_nested_fields(wip_field)
        else:
            return wip_field

    # e.g. parentField { nested {anotherLevel} }
    # 1. Remove spaces = parentField{nested{anotherLevel}}
    json_field_path = re.sub(r"\s", "", field)
    # 2. Replace curly braces with _ e.g. parentField_nested_anotherLevel
    return resolve_nested_fields(json_field_path)


def get_graphql_result_value(graphql_result, graphql_query_field):
    def resolve_field_value(result, field_pointers):
        if result and field_pointers:
            next_pointer = field_pointers.pop(0)
            result = resolve_field_value(result.get(next_pointer), field_pointers)

        return result

    graph_field_pointers = get_flattened_json_path(graphql_query_field).split('_')
    return resolve_field_value(graphql_result, graph_field_pointers)

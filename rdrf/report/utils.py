from importlib import import_module

from django.conf import settings


def load_report_configuration():
    report_config_module = import_module(settings.REPORT_CONFIG_MODULE)
    get_report_config_func = getattr(report_config_module, settings.REPORT_CONFIG_METHOD_GET)
    return get_report_config_func()

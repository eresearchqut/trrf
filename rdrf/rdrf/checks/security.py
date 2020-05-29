import os

from django.conf import settings
from django.core.checks import Error, register
from django.urls import get_resolver, URLPattern, URLResolver


@register()
def url_whitelist_check(app_configs, **kwargs):
    registered_names = set()

    def get_url_names(patterns, prefix=""):
        for pattern in patterns:
            if isinstance(pattern, URLPattern) and pattern.name:
                registered_names.add(f"{prefix}{pattern.name}")
            elif isinstance(pattern, URLResolver):
                get_url_names(pattern.url_patterns, f"{prefix}{pattern.namespace}:" if pattern.namespace else prefix)

    get_url_names(get_resolver().url_patterns)

    with open(os.path.join(settings.WEBAPP_ROOT, "rdrf/checks/url_whitelist.txt"), 'r') as f:
        whitelisted_names = set((line.rstrip() for line in f.readlines()))

    errors = []
    for name in whitelisted_names.symmetric_difference(registered_names):
        errors.append(Error(
            f"Url {name} has not been whitelisted",
            hint="Read the instructions in SECURITY.rst",
            id='trrf.E001',
        ))
    return errors

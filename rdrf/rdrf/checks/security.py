from django.core.checks import Error, register
from django.urls import get_resolver, URLPattern, URLResolver
from django.conf import settings


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

    return [
        Error(
            f"Url {name} has not been whitelisted",
            hint="Read the instructions in docs/security/README.rst",
            id='trrf.E001',
        ) for name in registered_names - set(settings.SECURITY_WHITELISTED_URLS)
    ]

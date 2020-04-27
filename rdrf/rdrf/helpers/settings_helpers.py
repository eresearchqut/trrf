from urllib.parse import urlparse


def get_static_url_domain(url):
    if not url:
        return None
    result = urlparse(url)
    return f"{result.scheme}://{result.netloc}"


def get_csp(static_params, dynamic_params):
    """
    Create a CSP from a list of static params and a list of dynamic params,
    where the dynamic params may contain `None` values
    """
    return static_params + [p for p in dynamic_params if p]

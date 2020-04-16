from urllib.parse import urlparse


def get_static_url_domain(url):
    if not url:
        return None
    result = urlparse(url)
    return f"{result.scheme}://{result.netloc}"

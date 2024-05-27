from django import template
from django.conf import settings
from django.utils.translation.trans_real import parse_accept_lang_header, language_code_re

register = template.Library()


@register.simple_tag(takes_context=True)
def get_user_requested_language(context):
    request = context['request']
    # 1. If user has activated a language, this takes precedence as the requested language
    site_language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
    if site_language:
        return site_language

    # 2. Otherwise, get the default browser language
    accept = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    for accept_lang, unused in parse_accept_lang_header(accept):
        if accept_lang == '*':
            break

        if not language_code_re.search(accept_lang):
            continue

        try:
            return accept_lang
        except LookupError:
            continue

    # Not expected to get to this point, but if so then use the default language
    return settings.LANGUAGE_CODE

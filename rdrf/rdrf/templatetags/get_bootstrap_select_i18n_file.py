from django import template
from django.utils.translation import to_locale

register = template.Library()


@register.filter()
def get_bootstrap_select_i18n_file(language):
    return f'/static/vendor/bootstrap-select-1.14.0-beta3/js/i18n/defaults-{to_locale(language)}.js'

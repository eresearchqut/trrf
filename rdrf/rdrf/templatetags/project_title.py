from django import template
from django.conf import settings
from django.utils.translation import gettext as _

register = template.Library()


@register.simple_tag
def project_title():
    if settings.PROJECT_TITLE is not None:
        return _("%s" % (settings.PROJECT_TITLE))

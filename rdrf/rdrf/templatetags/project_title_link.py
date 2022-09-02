from django import template
from django.conf import settings
from django.urls import reverse

register = template.Library()


@register.simple_tag
def project_title_link():
    args = settings.PROJECT_TITLE_LINK
    if isinstance(args, dict):
        return reverse(**args)
    else:
        return reverse(args)

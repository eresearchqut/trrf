from django import template

from rdrf.models.definition.models import Language

register = template.Library()


@register.filter()
def get_language(language_code):
    return Language.objects.get(language_code=language_code)

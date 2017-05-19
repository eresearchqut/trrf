from django import template
from django.conf import settings

register = template.Library()

@register.filter(name='add_language_modifier')
def add_language_modifier(file_name, request):
    """
    If the request ACCEPT_LANGUAGE header is non english then return a different file name
    """
    allowed_languages = [pair[0].upper() for pair in settings.LANGUAGES]
    language = request.META.get("HTTP_ACCEPT_LANGUAGE", "EN").upper()
    if "-" in language:
        # cases like en-US, de-CH
        language = language.split("-")[0]
        
    if language != "EN":
        if language in allowed_languages:
            # docs/filename  -> docs/DE_filename
            
            return language + "_" + file_name
    return file_name

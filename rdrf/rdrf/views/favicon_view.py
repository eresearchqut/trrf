from django.http import HttpResponsePermanentRedirect
from django.templatetags.static import static


def redirect_to_static(request):
    return HttpResponsePermanentRedirect(
        redirect_to=static("icons/favicon.ico")
    )

import logging

from django.shortcuts import redirect, render

logger = logging.getLogger(__name__)


def handler_csrf(request, reason):
    return redirect("login_router")


def handler_exceptions(request):
    raise Exception("Forced exception in /raise")


def handler404(request, exception):
    return render(request, "404.html")


def handler500(request, exception=None):
    logger.exception('Unhandled Exception!')
    return render(request, "500.html")


def handler_application_error(request):
    return render(request, "rdrf_cdes/application_error.html", {
        "application_error": "Example config Error",
    })

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.base import View

from rdrf.security.mixins import SuperuserRequiredMixin

logger = logging.getLogger(__name__)


class ImportRegistryView(SuperuserRequiredMixin, View):
    def get(self, request):
        state = request.GET.get("state", "ready")
        user = get_user_model().objects.get(username=request.user)
        error_message = request.GET.get("error_message", None)

        context = {
            "user_obj": user,
            "state": state,
            "error_message": error_message,
        }

        return render(request, "rdrf_cdes/import_registry.html", context)

    def post(self, request, *args, **kwargs):
        registry_yaml = request.POST["registry_yaml"]

        from rdrf.services.io.defs.importer import Importer

        if request.FILES:
            registry_yaml = request.FILES["registry_yaml_file"].read()

        try:
            importer = Importer()

            importer.load_yaml_from_string(registry_yaml)
            with transaction.atomic():
                importer.create_registry()

        except Exception as ex:
            logger.error("Import failed: %s" % ex, exc_info=ex)
            url_params = {
                "state": "fail",
                "error_message": str(ex),
            }
            import urllib.error
            import urllib.parse
            import urllib.request

            url_string = urllib.parse.urlencode(url_params)

            return HttpResponseRedirect(
                reverse("import_registry") + "?" + url_string
            )

        return HttpResponseRedirect(
            reverse("import_registry") + "?state=success"
        )

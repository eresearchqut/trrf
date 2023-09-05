from django.shortcuts import render, get_object_or_404
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.template import Template, Context
import logging

from rdrf.models.definition.models import Registry

logger = logging.getLogger(__name__)


class RegistryView(View):

    def get(self, request, registry_code):
        registry_model = get_object_or_404(Registry, code=registry_code)

        context = {
            'splash_screen': Template(registry_model.splash_screen).render(Context({'home_page_link': request.user.default_page})),
            'registry_code': registry_code,
            'state': "ok",
        }

        context.update(csrf(request))
        return render(request, 'rdrf_cdes/splash.html', context)

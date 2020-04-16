from csp.decorators import csp_update
from django.shortcuts import render
from django.views.generic.base import View
from rdrf.models.definition.models import Registry


class LandingView(View):
    @csp_update(DEFAULT_SRC=('https://fonts.googleapis.com', 'https://fonts.gstatic.com'))
    def get(self, request):
        return render(request, 'rdrf_cdes/index.html', {
            "registries": list(Registry.objects.all())
        })

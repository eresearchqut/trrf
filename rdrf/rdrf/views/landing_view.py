from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.generic.base import View
from rdrf.models.definition.models import Registry


class LandingView(View):
    @cache_control(public=True, max_age=86400)
    def get(self, request):
        return render(request, 'rdrf_cdes/index.html', {
            "registries": list(Registry.objects.all())
        })

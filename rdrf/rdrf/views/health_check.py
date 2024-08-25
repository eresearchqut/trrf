from django.http import JsonResponse

from rdrf.models.definition.models import Registry


def health_check(request):
    return JsonResponse(
        {
            "success": True,
            "hosted_registries_count": Registry.objects.count(),
        }
    )

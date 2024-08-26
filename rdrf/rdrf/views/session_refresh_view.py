from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def session_refresh(request):
    num_retries = request.session.get("num_retries")
    forced_refresh = request.GET.get("forced_refresh", "")
    reset_num_retries = forced_refresh.lower() == "true"
    if num_retries is None or reset_num_retries:
        request.session["num_retries"] = settings.SESSION_REFRESH_MAX_RETRIES
        num_retries = settings.SESSION_REFRESH_MAX_RETRIES
    elif num_retries > 0:
        num_retries -= 1
        request.session["num_retries"] = num_retries

    return JsonResponse(
        {"success": num_retries > 0, "retries_left": num_retries}
    )

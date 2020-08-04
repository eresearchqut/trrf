from django.http import JsonResponse
from django.views.decorators.http import require_GET

_MAX_REFRESH_RETRIES = 3


@require_GET
def session_refresh(request):
    num_retries = request.session.get('num_retries')
    if num_retries is None:
        request.session['num_retries'] = _MAX_REFRESH_RETRIES
        num_retries = _MAX_REFRESH_RETRIES
    elif num_retries > 0:
        num_retries -= 1
        request.session['num_retries'] = num_retries

    return JsonResponse({
        'success': num_retries > 0,
        'retries_left': num_retries
    })

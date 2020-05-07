import logging
from django.http import HttpResponseRedirect
from django.urls import reverse, resolve
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class EnforceTwoFactorAuthMiddleware(MiddlewareMixin):
    """
    This must be installed after
    :class:`~django.contrib.auth.middleware.AuthenticationMiddleware` and
    :class:`~django_otp.middleware.OTPMiddleware`.
    Users who are required to have two-factor authentication but aren't verified
    will always be redirected to the two-factor setup page.
    """

    def process_request(self, request):
        whitelisted_views = (
            'two_factor:login',
            'two_factor:setup',
            'two_factor:qr',
            'logout',
            'javascript-catalog',
            'js_reverse')
        if any([reverse(v) in request.path_info for v in whitelisted_views]):
            return None

        user = getattr(request, 'user', None)
        if user is None or user.is_anonymous:
            return None

        if not user.is_verified() and user.require_2_fact_auth:
            return HttpResponseRedirect(reverse('two_factor:setup'))

        return None


class NoCacheMiddleware:
    """
    Disable browser-side caching of all views. Override with
    :func:`~django.views.decorators.cache.cache_control` decorator
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not response.has_header('Cache-Control'):
            add_never_cache_headers(response)
        return response


class ForcePasswordResetMiddleware(MiddlewareMixin):
    def process_request(self, request):
        whitelisted_views = (
            'force_password_reset',
            'password_reset_done',
            'password_reset_confirm',
            'password_reset_complete',
            'javascript-catalog',
            'js_reverse')

        match = resolve(request.path)
        if match.url_name in whitelisted_views:
            return None

        user = getattr(request, 'user', None)
        if user is None or user.is_anonymous:
            return None

        if user.force_password_reset:
            return HttpResponseRedirect(reverse('force_password_reset'))

        return None

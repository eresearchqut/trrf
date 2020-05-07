import logging
from django.http import HttpResponseRedirect
from django.urls import reverse, resolve
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class UserSentryMiddleware(MiddlewareMixin):
    """
    This must be installed after
    :class:`~django.contrib.auth.middleware.AuthenticationMiddleware` and
    :class:`~django_otp.middleware.OTPMiddleware`.
    Users who are required to have two-factor authentication but aren't verified
    will always be redirected to the two-factor setup page.
    Users who are required to reset their passwords will be redirected to the
    password reset page
    """

    whitelisted_views = [
        'login',
        'setup',
        'qr',

        'force_password_reset',
        'password_reset_done',
        'password_reset_confirm',
        'password_reset_complete',

        'logout',
        'javascript-catalog',
        'js_reverse']

    def process_request(self, request):
        match = resolve(request.path)
        if match.url_name in self.whitelisted_views:
            return None

        user = getattr(request, 'user', None)
        if user is None or user.is_anonymous:
            return None

        for f in [self.verify_tfa, self.verify_password_reset]:
            if redirect := f(user):
                return redirect

        return None

    @staticmethod
    def verify_tfa(user):
        if not user.is_verified() and user.require_2_fact_auth:
            return HttpResponseRedirect(reverse('two_factor:setup'))

    @staticmethod
    def verify_password_reset(user):
        if user.force_password_reset:
            return HttpResponseRedirect(reverse('force_password_reset'))


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

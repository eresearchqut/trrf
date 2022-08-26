import logging
from django.http import HttpResponseRedirect
from django.urls import reverse, resolve
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin

from aws_xray_sdk import global_sdk_config
from aws_xray_sdk.core import xray_recorder

logger = logging.getLogger(__name__)


class XrayMetadataMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if global_sdk_config.sdk_enabled():
            document = xray_recorder.current_segment()
            if user := getattr(request, 'user', None):
                document.set_user(user)

        return response


class XrayExceptionMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if not global_sdk_config.sdk_enabled():
            return

        while xray_recorder.current_subsegment():
            xray_recorder.end_subsegment()


class UserSentryMiddleware(MiddlewareMixin):
    """
    This must be installed after
    :class:`~django.contrib.auth.middleware.AuthenticationMiddleware` and
    :class:`~django_otp.middleware.OTPMiddleware`.
    Users who are required to have two-factor authentication but aren't verified
    will always be redirected to the two-factor setup page.
    Users who are required to change their passwords will be redirected to the
    password reset page
    """

    whitelisted_views = [
        'login',
        'setup',
        'qr',

        'password_change',
        'password_change_done',

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

        for f in [self.verify_password_change, self.verify_tfa]:
            if redirect := f(user):
                return redirect

        return None

    @staticmethod
    def verify_tfa(user):
        if not user.is_verified() and user.require_2_fact_auth:
            return HttpResponseRedirect(reverse('two_factor:setup'))

    @staticmethod
    def verify_password_change(user):
        if user.force_password_change:
            return HttpResponseRedirect(reverse('password_change'))


class LaxSameSiteCookieMiddleware(MiddlewareMixin):
    """
    Sets 'SameSite: Lax' on cookies when resetting user passwords,
    and when logging in during passwordless registration.
    Must be installed before SessionMiddleware.

    This mitigates a bug where redirect-urls from email clients cause cookies
    to not be set when part of a redirect chain.
    """
    applied_views = [
        'password_reset_confirm',
        'registration_activate',
        'registration_activation_complete',
    ]

    def process_response(self, request, response):
        match = resolve(request.path)
        if match.url_name in self.applied_views:
            for cookie in response.cookies:
                response.cookies[cookie]['samesite'] = 'Lax'
        return response


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

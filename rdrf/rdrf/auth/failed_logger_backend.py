import datetime
import logging

from useraudit.backend import AuthFailedLoggerBackend

from django.conf import settings
from django.utils.timezone import now


from rdrf.models.definition.models import DeviceCookie

logger = logging.getLogger(__name__)


class FailedLoggerBackend(AuthFailedLoggerBackend):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = None

    def _fetch_device_cookie(self, cookie_val):
        return DeviceCookie.objects.filter(
            user=self._get_user(), cookie=cookie_val
        ).first() if cookie_val else None

    def _get_request_cookie(self):
        if self.request:
            return self.request.COOKIES.get(settings.DEVICE_COOKIE_NAME)
        return None

    def authenticate(self, request=None, **credentials):
        # This is called only for failed logins
        self.request = request
        return super().authenticate(request, **credentials)

    def is_attempts_exceeded(self):
        no_more_attempts = super().is_attempts_exceeded()
        device_cookie = None
        if no_more_attempts:
            device_cookie = self._fetch_device_cookie(self._get_request_cookie())
            is_locked_out = device_cookie and device_cookie.locked_out
            if not device_cookie or is_locked_out:
                # Don't lock the acount if no device cookie
                # in the request or it's aready locked out
                # but set a lockout on the user logins from
                # untrusted sources
                current_user = self._get_user()
                if current_user:
                    current_user.untrusted_source_login = False
                    lockout_ts = now() + datetime.timedelta(seconds=settings.USER_LOGIN_LOCKOUT_SECONDS)
                    current_user.untrusted_sources_lockout_expiration = lockout_ts
                    current_user.save()

                return False

            if device_cookie:
                # if a valid device cookie was present
                # and failed attempts are exceeded
                # put it in lockout mode for the configured
                # time interval
                device_cookie.locked_out = True
                expiration_dt = now() + datetime.timedelta(seconds=settings.DEVICE_COOKIE_LOCKOUT_SECONDS)
                device_cookie.lock_out_expiration = expiration_dt
                device_cookie.save()
                return False

        return no_more_attempts

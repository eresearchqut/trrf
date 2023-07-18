import hashlib
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def check_breaches(password):
    api = PwnedPasswordsApi()

    prefix, suffix = _hashed_components(password)
    result = api.range(prefix)

    return _result_to_dict(result).get(suffix.upper(), 0)


def _hashed_components(password, slice_index=5):
    sha1_password = hashlib.sha1(password.encode("utf8")).hexdigest()
    return sha1_password[:slice_index], sha1_password[slice_index:]


def _result_to_dict(result):
    def convert_password_tuple(value):
        hash_suffix, count = value.decode().split(":")
        return hash_suffix.upper(), int(count)

    return dict(map(convert_password_tuple, result.splitlines()))


class PwnedPasswordsApi:
    RANGE_URI = 'range'

    def __init__(self):
        self.base_url = settings.BREACHED_PASSWORD_ENDPOINT
        self.add_padding = True

    def range(self, hash_prefix):
        range_endpoint = self._url(self.RANGE_URI, hash_prefix)
        response = requests.get(range_endpoint, headers=self._request_headers())
        if response.status_code == 200:
            return response.content

    def _url(self, endpoint, *components):
        return f'{self.base_url}/{endpoint}/{"/".join(components)}'

    def _request_headers(self):
        return {
            'Add-Padding': f'{str(self.add_padding).lower()}'
        }

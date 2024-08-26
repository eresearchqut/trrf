import logging

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

logger = logging.getLogger(__name__)


def check_token(username_b64, token, max_token_age):
    assert max_token_age, "Max token age is required"
    try:
        username = force_str(urlsafe_base64_decode(username_b64))
        key = f"{username}:{token}"
        TimestampSigner().unsign(key, max_age=max_token_age)
    except (BadSignature, SignatureExpired):
        return False, username
    return True, username


def make_token(username):
    token_username, token = TimestampSigner().sign(username).split(":", 1)
    assert (
        username == token_username
    ), "Something went wrong with token generation"
    return token


def make_token_authenticated_link(viewname, username, token):
    username_b64 = urlsafe_base64_encode(force_bytes(username))
    return reverse(
        viewname, kwargs={"username_b64": username_b64, "token": token}
    )

from datetime import datetime, timedelta
from functools import reduce
from importlib import import_module

from django.conf import settings
from django.contrib.auth import authenticate, login

from django.test.client import RequestFactory


def is_recent(time):
    return datetime.now() - timedelta(seconds=3) < time


def simulate_login(username, password, headers=None):
    rf = RequestFactory()
    request = rf.request(**headers)
    engine = import_module(settings.SESSION_ENGINE)
    request.session = engine.SessionStore()

    if user := authenticate(request, username=username, password=password):
        login(request, user)


def chain_maps(*args):
    """Similar to collections.ChainMap but returned map is a separate copy (ie. changes
    to original dicts don't change the dict returned from this function)."""
    def merge(d1, d2):
        d1.update(d2)
        return d1

    return reduce(merge, reversed(args), {})

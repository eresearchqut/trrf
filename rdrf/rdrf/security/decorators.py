from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test as django_user_passes_test
from django.core.exceptions import PermissionDenied


def user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that ensures a view can be view only if the user passes the given test.
    Works slightly different than the Django one in raising PermissionDenied if the user is
    authenticated and redirecting to the login page only if the user isn't authenticated.
    The Django provided decorator always redirects to the login page even if the user is already
    authenticated.
    The decorator calls the Django provided decorator in case a redirect to login is needed,
    so that we don't duplicate the login redirection code in there.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and not test_func(request.user):
                raise PermissionDenied()

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return lambda view: decorator(django_user_passes_test(test_func, login_url, redirect_field_name)(view))


def _make_decorator(test_func):
    def decorator(view_function=None, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
        actual_decorator = user_passes_test(
            test_func,
            login_url=login_url,
            redirect_field_name=redirect_field_name,
        )
        if view_function:
            return actual_decorator(view_function)
        return actual_decorator

    return decorator


superuser_required = _make_decorator(lambda u: u.is_superuser)
staff_member_required = _make_decorator(lambda u: u.is_superuser or u.is_staff)

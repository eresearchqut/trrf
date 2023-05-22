from django.contrib.auth.mixins import UserPassesTestMixin, AccessMixin


class SuperuserRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_superuser


class StaffMemberRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff


class TokenAuthenticatedMixin(AccessMixin):
    # Inputs
    max_age = None

    # Outputs
    username_b64 = None
    token = None
    user = None
    is_valid_token = False

    def dispatch(self, request, *args, **kwargs):
        from rdrf.auth.signed_url.util import check_token
        from registry.groups.models import CustomUser
        from django.shortcuts import get_object_or_404

        if request.user.is_authenticated:
            self.user = request.user
        else:
            self.username_b64 = kwargs.get('username_b64')
            self.token = kwargs.get('token')

            self.is_valid_token, self.username = check_token(self.username_b64, self.token, self.max_age)
            self.user = get_object_or_404(CustomUser, username=self.username, is_active=True)

            if not self.is_valid_token:
                raise Exception('Invalid token')

        return super().dispatch(request, *args, **kwargs)

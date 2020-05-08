from django.contrib.auth.mixins import UserPassesTestMixin


class SuperuserRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_superuser


class StaffMemberRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff


class ReportAccessMixin(UserPassesTestMixin):

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        if not user.is_staff:
            return False
        if user.is_curator or user.is_clinician:
            return True
        return False

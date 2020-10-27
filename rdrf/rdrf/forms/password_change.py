from django.contrib.auth.forms import PasswordChangeForm as BasePasswordChangeForm
from django.forms import HiddenInput


class PasswordChangeForm(BasePasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        if not self.user.has_usable_password():
            self.fields["old_password"].widget = HiddenInput()
            self.fields["old_password"].required = False

    def clean_old_password(self):
        return "" if not self.user.has_usable_password() else super().clean_old_password()

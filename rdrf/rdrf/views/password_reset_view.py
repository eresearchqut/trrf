from django.contrib.auth.views import PasswordResetView


class ForcePasswordResetView(PasswordResetView):
    template_name = 'registration/force_password_reset_form.html'

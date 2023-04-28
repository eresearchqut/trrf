import logging

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import Form, EmailField, EmailInput, BooleanField, CharField, PasswordInput

from django.utils.translation import gettext_lazy as _

from registry.groups.models import CustomUser
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


class EmailChangeForm(Form):

    error_messages = {
        'duplicate_email': _('This email address is already in use by another user'),
        'email_mismatch': _('New email address and confirm email address do not match.'),
        'incorrect_password': _('Your current password is incorrect'),
    }

    new_email = EmailField(label=_('New email'), max_length=254, widget=EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}))
    new_email2 = EmailField(label=_('Confirm new email'), max_length=254, widget=EmailInput(attrs={'autocomplete': 'email'}))
    current_password = CharField(label=_('Current password'), widget=PasswordInput())
    confirm_submit = BooleanField(label=_('I confirm that my new email address will become my new username when I next log in to this site.'))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        email = self.cleaned_data.get('new_email')

        # Excluding the current user, are there any users with the same email?
        duplicate_users = CustomUser.objects\
            .exclude(username__iexact=self.user.username)\
            .filter(Q(username__iexact=email) | Q(email__iexact=email))

        if duplicate_users:
            raise ValidationError(self.error_messages['duplicate_email'])

        # Excluding the current patient (if applicable), are there any patients with the same email?
        if self.user.patient:
            duplicate_patients = Patient.objects.exclude(email__iexact=self.user.patient.email).filter(email__iexact=email)

            if duplicate_patients:
                raise ValidationError(self.error_messages['duplicate_email'])

        return email

    def clean_new_email2(self):
        new_email = self.cleaned_data.get('new_email')
        new_email2 = self.cleaned_data.get('new_email2')

        if new_email and new_email2 != new_email:
            raise ValidationError(self.error_messages['email_mismatch'])

        return new_email2

    def clean_current_password(self):
        password = self.cleaned_data['current_password']
        if not self.user.check_password(password):
            raise ValidationError(self.error_messages['incorrect_password'])
        return password

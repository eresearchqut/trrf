import logging

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import Form, EmailField, EmailInput, CharField, PasswordInput, RadioSelect, TypedChoiceField
from django.utils.translation import gettext_lazy as _

from rdrf.helpers.registry_features import RegistryFeatures
from registry.groups.models import CustomUser
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


class EmailChangeForm(Form):

    error_messages = {
        'duplicate_email': _('This email address is already in use by another user'),
        'email_mismatch': _('New email address and confirm email address do not match.'),
        'incorrect_password': _('Your current password is incorrect'),
        'inactive_user': _('An email change request requiring activation cannot be submitted for an inactive user.'),
    }

    ACTIVATION_CHOICES = ((False, _('Complete request without requiring user to activate')),
                          (True, _('Require user to activate this email change request')))

    new_email = EmailField(label=_('New email / username'), max_length=254, widget=EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}))
    new_email2 = EmailField(label=_('Confirm new email'), max_length=254, widget=EmailInput(attrs={'autocomplete': 'email'}))
    current_password = CharField(label=_('Current password'), widget=PasswordInput())
    user_activation_required = TypedChoiceField(coerce=lambda value: value == str(True),
                                                choices=ACTIVATION_CHOICES,
                                                label=_('User Activation Method'),
                                                widget=RadioSelect,
                                                initial=False)

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user')
        self.user = kwargs.pop('user')

        super().__init__(*args, **kwargs)

        self.fields['user_activation_required'].required = self.is_activation_optional
        self.fields['current_password'].required = not self.current_user.is_staff

    @property
    def is_activation_optional(self):
        return self.current_user.is_staff \
            and self.user.my_registry \
            and self.user.my_registry.has_feature(RegistryFeatures.PATIENT_EMAIL_ACTIVATION_OPTIONAL_FOR_ADMIN)

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
        if self.fields['current_password'].required and not self.current_user.check_password(password):
            raise ValidationError(self.error_messages['incorrect_password'])
        return password

    def clean_user_activation_required(self):
        if self.is_activation_optional:
            return self.cleaned_data['user_activation_required']
        return True

    def clean(self):
        if not self.user.is_active and self.cleaned_data['user_activation_required']:
            raise ValidationError(self.error_messages['inactive_user'])

        return super().clean()

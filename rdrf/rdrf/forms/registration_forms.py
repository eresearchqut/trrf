from django.forms import CharField, ChoiceField, DateField, ValidationError
from django.forms.widgets import EmailInput, RadioSelect
from django.utils.translation import gettext as _

from registration.users import UsernameField, UserModel
from registration.forms import RegistrationForm
from rdrf.helpers.utils import get_preferred_languages
from registry.patients.models import Patient


def _tuple(code, name):
    return code, _(name)


def _preferred_languages():
    languages = get_preferred_languages()
    return [_tuple(l.code, l.name) for l in languages] if languages else [_tuple('en', 'English')]


User = UserModel()


class RegistrationFormCaseInsensitiveCheck(RegistrationForm):
    """
    A subclass of :class:`RegistrationForm` with insensitive check of usernames (emails)
    """
    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        search_dict = {
            f"{UsernameField()}__iexact": username.lower()
        }
        if User.objects.filter(**search_dict).exists():
            raise ValidationError(_('Email already exists !'))

        return username


class PatientRegistrationForm(RegistrationFormCaseInsensitiveCheck):

    placeholders = {
        'username': _("Username"),
        'password1': _("Password"),
        'password2': _("Repeat Password"),
        'first_name': _("Given Names"),
        'surname': _("Surname"),
        'date_of_birth': _("Date of Birth"),
    }

    no_placeholder_fields = ['gender']

    language_choices = _preferred_languages()

    password_fields = ['password1', 'password2']

    tooltip_info = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_fields()

    def setup_fields(self):
        self.fields['username'].widget = EmailInput(attrs={})
        for field in self.fields:
            if field not in self.no_placeholder_fields:
                self.fields[field].widget.attrs['class'] = 'form-control'
                self.fields[field].widget.attrs['placeholder'] = self.placeholders.get(field, _(''))
            if field in self.password_fields:
                self.fields[field].widget.render_value = True

    registry_code = CharField(required=True)
    first_name = CharField(required=True, max_length=30)
    surname = CharField(required=True, max_length=30)
    date_of_birth = DateField(required=True)
    gender = ChoiceField(choices=Patient.SEX_CHOICES, widget=RadioSelect, required=True)
    preferred_languages = ChoiceField(required=False, choices=language_choices)


class ParentWithPatientRegistrationForm(PatientRegistrationForm):

    PatientRegistrationForm.placeholders.update({
        'parent_guardian_first_name': _("Parent/Guardian Given Names"),
        'parent_guardian_last_name': _("Parent/Guardian Surname"),
        'parent_guardian_date_of_birth': _("Parent/Guardian Date of Birth"),
        'parent_guardian_gender': _("Parent/Guardian gender"),
    })

    PatientRegistrationForm.no_placeholder_fields.extend(['parent_guardian_gender'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field, tooltip in self.tooltip_info.items():
            self.fields[field].widget.attrs['data-toggle'] = 'tooltip'
            self.fields[field].widget.attrs['data-placement'] = 'left'
            self.fields[field].widget.attrs['title'] = tooltip

    parent_guardian_first_name = CharField(required=True)
    parent_guardian_last_name = CharField(required=True)
    parent_guardian_date_of_birth = DateField(required=True)
    parent_guardian_gender = ChoiceField(choices=Patient.SEX_CHOICES, widget=RadioSelect, required=True)

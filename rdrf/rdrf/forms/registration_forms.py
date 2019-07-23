from django.forms import CharField, ChoiceField, DateField, BooleanField, ValidationError
from django.forms.widgets import RadioSelect, Select, EmailInput
from django.utils.translation import gettext as _

from registration.forms import RegistrationForm
from rdrf.helpers.utils import country_choices, get_preferred_languages
from registry.patients.models import Patient
from rdrf.forms.widgets.widgets import CountryWidget


def _tuple(code, name):
    return code, _(name)


def _preferred_languages():
    languages = get_preferred_languages()
    return [_tuple(l.code, l.name) for l in languages] if languages else [_tuple('en', 'English')]


class RestrictedCountryMixin:

    def set_restricted_countries(self, field_name):
        self.fields[field_name].widget.set_restricted_countries(self.restricted_countries)
        if self.restricted_countries:
            self.fields[field_name].choices = [(c, c) for c in self.restricted_countries]
        else:
            self.fields[field_name].choices = country_choices()

    def country_validation(self, field_name, error_message):
        if self.restricted_countries:
            country = self.data[field_name]
            if country and country not in self.restricted_countries:
                raise ValidationError(error_message)


class PatientRegistrationForm(RegistrationForm, RestrictedCountryMixin):

    placeholders = {
        'username': _("Username"),
        'password1': _("Password"),
        'password2': _("Repeat Password"),
        'first_name': _("Given Names"),
        'surname': _("Surname"),
        'date_of_birth': _("Date of Birth"),
        'address': _("Address"),
        'suburb': _("Suburb / Town"),
        'state': _("State / County / Province / Region"),
        'postcode': _("Zip / Postal Code"),
        'phone_number': _('Phone Number')
    }

    no_placeholder_fields = ['gender']

    language_choices = _preferred_languages()

    password_fields = ['password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_fields()

    def setup_fields(self):
        self.fields['username'].widget = EmailInput(attrs={})
        self.restricted_countries = []
        for field in self.fields:
            if field not in self.no_placeholder_fields:
                self.fields[field].widget.attrs['class'] = 'form-control'
                self.fields[field].widget.attrs['placeholder'] = self.placeholders.get(field, _(''))
            if field in self.password_fields:
                self.fields[field].widget.render_value = True

    def set_registry(self, registry):
        self.restricted_countries = registry.get_restricted_countries()
        self.set_restricted_countries('country')

    def clean(self):
        self.country_validation("country", "Country not in list of valid countries !")
        return super().clean()

    preferred_languages = ChoiceField(required=False, choices=language_choices)
    first_name = CharField(required=True, max_length=30)
    surname = CharField(required=True, max_length=30)
    date_of_birth = DateField(required=True)
    gender = ChoiceField(choices=Patient.SEX_CHOICES, widget=RadioSelect, required=True)
    address = CharField(required=True, max_length=100)
    suburb = CharField(required=True, max_length=30)
    country = ChoiceField(
        required=True,
        widget=CountryWidget(attrs={
            'empty_option_text': 'Country',
            'onchange': 'setUpStateOnCountryChange("#id_country", "#id_state")'
        }))
    state = CharField(required=True, widget=Select)
    postcode = CharField(required=True, max_length=30)
    phone_number = CharField(required=True, max_length=30)
    registry_code = CharField(required=True)


class ParentWithPatientRegistrationForm(PatientRegistrationForm, RestrictedCountryMixin):

    PatientRegistrationForm.placeholders.update({
        'parent_guardian_first_name': _("Parent/Guardian Given Names"),
        'parent_guardian_last_name': _("Parent/Guardian Surname"),
        'parent_guardian_date_of_birth': _("Parent/Guardian Date of Birth"),
        'parent_guardian_gender': _("Parent/Guardian gender"),
        'parent_guardian_address': _("Parent/Guardian Address"),
        'parent_guardian_suburb': _("Parent/Guardian Suburb / Town"),
        'parent_guardian_state': _("Parent/Guardian State / County / Province / Region"),
        'parent_guardian_postcode': _("Parent/Guardian Zip / Postal Code"),
        'parent_guardian_phone': _('Parent/Guardian Phone Number')
    })

    PatientRegistrationForm.no_placeholder_fields.extend(['parent_guardian_gender', 'same_address'])

    tooltip_info = {
        'parent_guardian_address': _("Please enter an address through which we can contact you"),
        'parent_guardian_phone': _('''Please enter a phone number through which we can contact you,
                                      including the country code (e.g. +61 for Australia)''')
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field, tooltip in self.tooltip_info.items():
            self.fields[field].widget.attrs['data-toggle'] = 'tooltip'
            self.fields[field].widget.attrs['data-placement'] = 'left'
            self.fields[field].widget.attrs['title'] = tooltip

    def set_registry(self, registry):
        super().set_registry(registry)
        self.set_restricted_countries('parent_guardian_country')

    parent_guardian_first_name = CharField(required=True)
    parent_guardian_last_name = CharField(required=True)
    parent_guardian_date_of_birth = DateField(required=True)
    parent_guardian_gender = ChoiceField(choices=Patient.SEX_CHOICES, widget=RadioSelect, required=True)
    parent_guardian_address = CharField(required=True, max_length=100)
    parent_guardian_suburb = CharField(required=True, max_length=30)
    parent_guardian_country = ChoiceField(
        required=True,
        widget=CountryWidget(attrs={
            'empty_option_text': 'Country',
            'onchange': 'setUpStateOnCountryChange("#id_parent_guardian_country", "#id_parent_guardian_state")'
        }))
    parent_guardian_state = CharField(required=False, widget=Select, max_length=30)
    parent_guardian_postcode = CharField(required=True, max_length=30)
    parent_guardian_phone = CharField(required=True, max_length=30)
    same_address = BooleanField(required=False)

    def clean(self):
        self.country_validation("parent_guardian_country", "Parent guardian country not in list of valid countries !")
        return super().clean()

    def _clean_fields(self):
        base_required_fields = ['address', 'suburb', 'country', 'state', 'postcode', 'phone_number']
        if self.data.get('same_address', False):
            for f in base_required_fields:
                self.fields[f].required = False
        super()._clean_fields()

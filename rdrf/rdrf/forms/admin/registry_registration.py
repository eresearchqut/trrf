from django.conf import settings
from django.forms import Form, BooleanField, ChoiceField, CharField, TextInput, Select, Textarea
from django.utils.translation import ugettext as _

_form_attrs = {
    "class": "form-control",
}
BootstrapTextInput = TextInput(attrs=_form_attrs)
BootstrapSelectInput = Select(attrs=_form_attrs)
BootstrapTextAreaInput = Textarea(attrs=_form_attrs)


class RegistrationAdminForm(Form):
    enable_registration = BooleanField(
        required=False,
        label=_('Enable registration feature'),
    )
    new_notification = BooleanField(
        required=False,
        label=_('Create a new email notification for patients upon registration'),
    )

    language = ChoiceField(required=False, choices=settings.ALL_LANGUAGES, widget=BootstrapSelectInput)
    description = CharField(required=False, widget=BootstrapTextInput)
    subject = CharField(required=False, max_length=50, widget=BootstrapTextInput)
    body = CharField(required=False, widget=BootstrapTextAreaInput)

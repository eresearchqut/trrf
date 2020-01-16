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

    from_address = CharField(required=False, widget=BootstrapTextInput, label=_("From address"))

    language = ChoiceField(required=False, choices=settings.ALL_LANGUAGES, widget=BootstrapSelectInput, label=_("Language"))
    description = CharField(required=False, widget=BootstrapTextInput, label=_("Description"))
    subject = CharField(required=False, max_length=50, widget=BootstrapTextInput, label=_("Subject"))
    body = CharField(required=False, widget=BootstrapTextAreaInput, label=_("Body"))

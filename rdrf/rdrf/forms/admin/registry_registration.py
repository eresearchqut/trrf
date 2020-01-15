from django.conf import settings

from django.forms import Form, BooleanField, ChoiceField, CharField, TextInput, Select, Textarea

_form_attrs = {
    "class": "form-control",
}
BootstrapTextInput = TextInput(attrs=_form_attrs)
BootstrapSelectInput = Select(attrs=_form_attrs)
BootstrapTextAreaInput = Textarea(attrs=_form_attrs)


class RegistrationAdminForm(Form):
    enable_registration = BooleanField(required=False, label='Enable registration feature')
    new_notification = BooleanField(required=False, label='Create an email notification for patients upon registration, with the template below')
    new_template_language = ChoiceField(required=False, choices=settings.ALL_LANGUAGES, widget=BootstrapSelectInput)
    new_template_description = CharField(required=False, widget=BootstrapTextInput)
    new_template_subject = CharField(required=False, max_length=50, widget=BootstrapTextInput)
    new_template_body = CharField(required=False, widget=BootstrapTextAreaInput)

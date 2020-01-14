from django.forms import Form, BooleanField


class RegistrationAdminForm(Form):
    enable_registration = BooleanField(label='Enable registration feature')
    new_notification = BooleanField(label='Create an email notification for patients upon registration')
    new_template = BooleanField(label='Create an email notification template for patients upon registration')

# Generated by Django 2.2.10 on 2020-02-24 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0121_email_template_defaults'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='default_for_notification',
            field=models.CharField(blank=True, choices=[('account-locked', 'Account Locked'), ('other-clinician', 'Other Clinician'), ('new-patient', 'New Patient Registered'), ('new-patient-parent', 'New Patient Registered (Parent)'), ('account-verified', 'Account Verified'), ('password-expiry-warning', 'Password Expiry Warning'), ('reminder', 'Reminder'), ('clinician-signup-request', 'Clinician Signup Request'), ('clinician-activation', 'Clinician Activation'), ('clinician-selected', 'Clinician Selected'), ('participant-clinician-notification', 'Participant Clinician Notification'), ('patient-consent-change', 'Patient Consent Change')], max_length=100, null=True),
        ),
    ]
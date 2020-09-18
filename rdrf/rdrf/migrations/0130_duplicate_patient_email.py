# Generated by Django 2.2.13 on 2020-09-18 10:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0129_survey_and_verifications_changes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailnotification',
            name='description',
            field=models.CharField(choices=[('account-locked', 'Account Locked'), ('other-clinician', 'Other Clinician'), ('new-patient', 'New Patient Registered'), ('new-patient-parent', 'New Patient Registered (Parent)'), ('account-verified', 'Account Verified'), ('password-expiry-warning', 'Password Expiry Warning'), ('reminder', 'Reminder'), ('clinician-signup-request', 'Clinician Signup Request'), ('clinician-activation', 'Clinician Activation'), ('clinician-selected', 'Clinician Selected'), ('participant-clinician-notification', 'Participant Clinician Notification'), ('patient-consent-change', 'Patient Consent Change'), ('new-carer', 'Primary Caregiver Registered'), ('carer-invited', 'Primary Caregiver Invited'), ('carer-assigned', 'Primary Caregiver Assigned'), ('carer-activated', 'Primary Caregiver Activated'), ('carer-deactivated', 'Primary Caregiver Deactivated'), ('survey-request', 'Survey Request'), ('duplicate-patient-set', 'Duplicate Patient Set')], max_length=100),
        ),
    ]

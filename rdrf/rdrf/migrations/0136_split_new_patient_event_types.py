# Generated by Django 2.2.25 on 2022-01-20 17:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0135_contextformgroup_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailnotification',
            name='description',
            field=models.CharField(choices=[('account-locked', 'Account Locked'), ('other-clinician', 'Other Clinician'), ('new-patient-user-registered', 'User associated with patient was created by registering ["registration" feature required]'), ('new-patient-parent', 'New Patient Registered (Parent)'), ('new-patient-user-added', 'User associated with patient was created on the "Add Patient Page" ["patients_create_users" feature required]'), ('account-verified', 'Account Verified'), ('password-expiry-warning', 'Password Expiry Warning'), ('reminder', 'Reminder'), ('clinician-signup-request', 'Clinician Signup Request'), ('clinician-activation', 'Clinician Activation'), ('clinician-selected', 'Clinician Selected'), ('participant-clinician-notification', 'Participant Clinician Notification'), ('patient-consent-change', 'Patient Consent Change'), ('new-carer', 'Primary Caregiver Registered'), ('carer-invited', 'Primary Caregiver Invited'), ('carer-assigned', 'Primary Caregiver Assigned'), ('carer-activated', 'Primary Caregiver Activated'), ('carer-deactivated', 'Primary Caregiver Deactivated'), ('survey-request', 'Survey Request'), ('duplicate-patient-set', 'Duplicate Patient Set'), ('clinician-assigned', 'Clinician Assigned'), ('clinician-unassigned', 'Clinician Unassigned')], max_length=100),
        ),
    ]

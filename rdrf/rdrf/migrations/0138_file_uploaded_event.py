# Generated by Django 2.2.25 on 2022-01-29 17:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0137_split_new_patient_event_types_data_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailnotification',
            name='file_uploaded_cdes',
            field=models.ManyToManyField(blank=True, help_text='Select File CDEs to be notified about. Leave empty to be notified on all file uploads<br />', limit_choices_to={'datatype': 'file'}, to='rdrf.CommonDataElement'),
        ),
        migrations.AlterField(
            model_name='emailnotification',
            name='description',
            field=models.CharField(choices=[('account-locked', 'Account Locked'), ('other-clinician', 'Other Clinician'), ('new-patient-user-registered', 'User associated with patient was created by registering ["registration" feature required]'), ('new-patient-parent', 'New Patient Registered (Parent)'), ('new-patient-user-added', 'User associated with patient was created on the "Add Patient Page" ["patients_create_users" feature required]'), ('account-verified', 'Account Verified'), ('password-expiry-warning', 'Password Expiry Warning'), ('reminder', 'Reminder'), ('clinician-signup-request', 'Clinician Signup Request'), ('clinician-activation', 'Clinician Activation'), ('clinician-selected', 'Clinician Selected'), ('participant-clinician-notification', 'Participant Clinician Notification'), ('patient-consent-change', 'Patient Consent Change'), ('new-carer', 'Primary Caregiver Registered'), ('carer-invited', 'Primary Caregiver Invited'), ('carer-assigned', 'Primary Caregiver Assigned'), ('carer-activated', 'Primary Caregiver Activated'), ('carer-deactivated', 'Primary Caregiver Deactivated'), ('survey-request', 'Survey Request'), ('duplicate-patient-set', 'Duplicate Patient Set'), ('clinician-assigned', 'Clinician Assigned'), ('clinician-unassigned', 'Clinician Unassigned'), ('file-uploaded', 'File Uploaded')], max_length=100),
        ),
    ]
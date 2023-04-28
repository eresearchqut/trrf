from registry.patients.models import Patient


def sync_user_email_update(user, new_email_address):
    user.username = new_email_address
    user.email = new_email_address
    user.save()

    if user.patient:
        patient = Patient.objects.get(user=user)
        patient.email = new_email_address
        patient.save()

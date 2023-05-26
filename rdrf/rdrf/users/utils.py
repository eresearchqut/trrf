import logging

from django.template.loader import get_template
from django.utils.translation import gettext as _

from rdrf.auth.signed_url.util import make_token, make_token_authenticated_link
from rdrf.events.events import EventType
from rdrf.helpers.utils import make_full_url
from rdrf.services.io.notifications.email_notification import process_notification_with_default
from registry.groups.models import EmailChangeRequest, EmailChangeRequestStatus
from registry.patients.models import Patient

logger = logging.getLogger(__name__)

EMAIL_CHANGE_REQUEST_EXPIRY_HOURS = 48
EMAIL_CHANGE_REQUEST_EXPIRY_SECONDS = 60 * 60 * EMAIL_CHANGE_REQUEST_EXPIRY_HOURS


def user_has_email_change_request(user):
    return hasattr(user, 'emailchangerequest')


def create_email_change_request(user, new_email_address):

    if user_has_email_change_request(user):
        user.emailchangerequest.delete()

    user.emailchangerequest = EmailChangeRequest(new_email=new_email_address,
                                                 current_username=user.username,
                                                 current_user_email=user.email,
                                                 current_patient_email=user.patient.email if user.patient else None,
                                                 status=EmailChangeRequestStatus.PENDING)

    user.emailchangerequest.save()

    send_email_change_request_notification(user)


def send_email_change_request_notification(user):
    email_template = get_template('registration/email_reset_activation.html')

    token = make_token(user.username)
    token_authenticated_link = make_token_authenticated_link(viewname='activate_email_request',
                                                             username=user.username,
                                                             token=token)
    activation_link = make_full_url(token_authenticated_link)

    process_notification_with_default(reg_code=user.registry_code,
                                      description=EventType.EMAIL_CHANGE_REQUEST,
                                      template_data={'user': user,
                                                     'activation_link': activation_link,
                                                     'expiration_hours': EMAIL_CHANGE_REQUEST_EXPIRY_HOURS,
                                                     'user_full_name': user.get_full_name()},
                                      default_template=email_template,
                                      default_subject=_('New Email Address Activation'),
                                      default_recipient=[user.emailchangerequest.new_email])


def send_email_change_request_completed_notification(user, user_previous_email):
    email_template = get_template('registration/email_reset_completed.html')

    process_notification_with_default(reg_code=user.registry_code,
                                      description=EventType.EMAIL_CHANGE_COMPLETE,
                                      template_data={'user': user,
                                                     'user_full_name': user.get_full_name(),
                                                     'registry': user.my_registry.name},
                                      default_template=email_template,
                                      default_subject=_('Change of Email Completed'),
                                      default_recipient=[user_previous_email])


def sync_user_email_update(user, new_email_address):

    previous_email = user.email

    user.username = new_email_address
    user.email = new_email_address
    user.save()

    if user.patient:
        patient = Patient.objects.get(user=user)
        patient.email = new_email_address
        patient.save()

    send_email_change_request_completed_notification(user, previous_email)


def activate_email_change_request(user):
    if user_has_email_change_request(user) and user.emailchangerequest.status == EmailChangeRequestStatus.PENDING:
        sync_user_email_update(user, user.emailchangerequest.new_email)
        user.emailchangerequest.status = EmailChangeRequestStatus.COMPLETED
        user.emailchangerequest.save()

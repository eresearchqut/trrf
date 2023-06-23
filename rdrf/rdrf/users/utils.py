import logging

from django.conf import settings
from django.dispatch import Signal
from django.template.loader import get_template
from django.utils.translation import gettext as _

from rdrf.auth.signed_url.util import make_token, make_token_authenticated_link
from rdrf.events.events import EventType
from rdrf.helpers.utils import make_full_url
from rdrf.services.io.notifications.email_notification import process_notification
from registry.groups.models import EmailChangeRequest, EmailChangeRequestStatus
from registry.patients.models import Patient

logger = logging.getLogger(__name__)

EMAIL_CHANGE_REQUEST_EXPIRY_HOURS = 48
EMAIL_CHANGE_REQUEST_EXPIRY_SECONDS = 60 * 60 * EMAIL_CHANGE_REQUEST_EXPIRY_HOURS


user_email_updated = Signal()


def initiate_email_change_request(user, new_email_address, requires_activation=True):
    _create_email_change_request(user, new_email_address)

    if requires_activation:
        _send_email_change_request_notification(user)
    else:
        _sync_user_email_update(user, new_email_address)
        _complete_change_request(user)


def activate_email_change_request(user):
    if _user_has_email_change_request(user) and user.emailchangerequest.status == EmailChangeRequestStatus.PENDING:
        _sync_user_email_update(user, user.emailchangerequest.new_email)
        _complete_change_request(user)
        _send_email_change_request_completed_notification(user, user.emailchangerequest.current_user_email)


def _user_has_email_change_request(user):
    return hasattr(user, 'emailchangerequest')


def _create_email_change_request(user, new_email_address):
    if _user_has_email_change_request(user):
        user.emailchangerequest.delete()

    user.emailchangerequest = EmailChangeRequest(new_email=new_email_address,
                                                 current_username=user.username,
                                                 current_user_email=user.email,
                                                 current_patient_email=user.patient.email if user.patient else None,
                                                 status=EmailChangeRequestStatus.PENDING)

    user.emailchangerequest.save()


def _complete_change_request(user):
    user.emailchangerequest.status = EmailChangeRequestStatus.COMPLETED
    user.emailchangerequest.save()


def _send_email_change_request_notification(user):
    email_template = get_template('registration/email_reset_activation.html')

    token = make_token(user.username)
    token_authenticated_link = make_token_authenticated_link(viewname='activate_email_request',
                                                             username=user.username,
                                                             token=token)
    activation_link = make_full_url(token_authenticated_link)
    email_recipient = {user.emailchangerequest.new_email: user.preferred_language}

    process_notification(reg_code=user.registry_code,
                         description=EventType.EMAIL_CHANGE_REQUEST,
                         template_data={'user': user,
                                        'activation_link': activation_link,
                                        'expiration_hours': EMAIL_CHANGE_REQUEST_EXPIRY_HOURS,
                                        'user_full_name': user.get_full_name()},
                         default_template=email_template,
                         default_subject=_('New Email Address Activation'),
                         mandatory_recipients=email_recipient)


def _send_email_change_request_completed_notification(user, user_previous_email):
    email_template = get_template('registration/email_reset_completed.html')
    email_recipient = {user_previous_email: user.preferred_language}

    if user.my_registry:
        registry_name = user.my_registry.name
    else:
        registry_name = settings.PROJECT_TITLE

    process_notification(reg_code=user.registry_code,
                         description=EventType.EMAIL_CHANGE_COMPLETE,
                         template_data={'user': user,
                                        'user_full_name': user.get_full_name(),
                                        'registry': registry_name},
                         default_template=email_template,
                         default_subject=_('Change of Email Completed'),
                         mandatory_recipients=email_recipient)


def _sync_user_email_update(user, new_email_address):
    user.username = new_email_address
    user.email = new_email_address
    user.save()

    if user.patient:
        patient = Patient.objects.get(user=user)
        patient.email = new_email_address
        patient.save()

    user_email_updated.send(sender=_sync_user_email_update, user=user)

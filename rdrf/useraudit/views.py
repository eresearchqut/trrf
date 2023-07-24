import logging

from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import LoginAttemptLogger

logger = logging.getLogger("django.security")

login_attempt_logger = LoginAttemptLogger()


def reactivate_user(request, user_id):
    user = _get_user(user_id)
    user.is_active = True
    user.save()
    login_attempt_logger.reset(user.username)
    return HttpResponseRedirect(reverse("admin:useraudit_loginattempt_changelist"))


def _get_user(user_id):
    UserModel = get_user_model()
    try:
        return UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        logger.warning("User model for user_id %d not found" % user_id)
        return None

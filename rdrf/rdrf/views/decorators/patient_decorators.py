import logging
from functools import wraps

from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.urls import reverse

from rdrf.models.definition.models import Registry

logger = logging.getLogger(__name__)


def patient_questionnaire_access(function):
    def is_patient(user):
        try:
            patient_group = Group.objects.get(name__icontains="patients")
        except (Group.DoesNotExist, Group.MultipleObjectsReturned):
            logger.error("Patients group must be configured")
            raise
        return user.groups.filter(id=patient_group.id).exists()

    @wraps(function)
    def _wrapped_view(*args, **kwargs):
        user = args[0].user
        registry_code = kwargs['registry_code']
        registry = get_object_or_404(Registry, code=registry_code)

        if not registry.questionnaire:
            return HttpResponseNotFound("Registry does not have a questionnaire")

        # fixme: check logic
        if registry.questionnaire.login_required and (not user.is_authenticated or not is_patient(user)):
            return HttpResponseRedirect(reverse("registry:patient_page", args={registry_code}))

        return function(*args, **kwargs)

    return _wrapped_view

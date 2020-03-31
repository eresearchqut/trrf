import logging

from django.core.exceptions import PermissionDenied
from registry.patients.models import ParentGuardian, Patient


logger = logging.getLogger(__name__)


def user_is_patient_type(user):
    return user.is_patient or user.is_parent or user.is_carrier or user.is_carer


def _security_violation(user, patient_model):
    logger.info(f"SECURITY VIOLATION User {user.pk} Patient {patient_model.pk}")
    raise PermissionDenied()


def _patient_checks(user, patient_model):
    # check patients who have registered as users with this user

    if patient_model.user == user:
        return True
    # check carer of patient
    if patient_model.carer == user:
        return True

    # check parent guardian self patient and own children
    for parent in ParentGuardian.objects.filter(user=user):
        if patient_model in parent.children:
            return True
        if parent.self_patient and parent.self_patient.pk == patient_model.pk:
            return True
    return False


def security_check_user_patient(user, patient_model):
    if not (user.is_authenticated and user.is_active):
        return False

    # either user is allowed to act on this record ( return True)
    # or not ( raise PermissionDenied error)
    if user.is_superuser:
        return True

    if user_is_patient_type(user):
        patient_check_result = _patient_checks(user, patient_model)
        if patient_check_result:
            return patient_check_result
        _security_violation(user, patient_model)

    if user.is_clinician:
        registry = patient_model.rdrf_registry.first()
        if not Patient.objects.get_by_clinician(user, registry).filter(pk=patient_model.pk).exists():
            _security_violation(user, patient_model)

    # user is staff of some sort
    patient_wg_ids = set([wg.id for wg in patient_model.working_groups.all()])
    user_wg_ids = set([wg.id for wg in user.working_groups.all()])

    overlap = patient_wg_ids & user_wg_ids

    if overlap:
        return True

    _security_violation(user, patient_model)


def can_sign_consent(user, patient_model):
    if user_is_patient_type(user):
        return _patient_checks(user, patient_model)
    return False


def get_object_or_permission_denied(klass, *args, **kwargs):
    """
    Use get() to return an object, or raise a PermissionDenied exception if the object
    does not exist. This is used to raise PermissionDenied for records which do not exist.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.

    Like with QuerySet.get(), MultipleObjectsReturned is raised if more than
    one object is found.
    """
    queryset = klass
    if hasattr(klass, '_default_manager'):
        queryset = klass._default_manager.all()
    if not hasattr(queryset, 'get'):
        klass__name = klass.__name__ if isinstance(klass, type) else klass.__class__.__name__
        raise ValueError(
            "First argument to get_object_or_404() must be a Model, Manager, "
            "or QuerySet, not '%s'." % klass__name
        )
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        raise PermissionDenied()

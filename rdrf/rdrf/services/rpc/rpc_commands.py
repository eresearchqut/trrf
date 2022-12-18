import logging

from django.core.exceptions import PermissionDenied

from rdrf.security.security_checks import security_check_user_patient

logger = logging.getLogger(__name__)


def rpc_get_forms_list(request, registry_code, patient_id, form_group_id):
    from rdrf.models.definition.models import ContextFormGroup
    from rdrf.models.definition.models import Registry
    from registry.patients.models import Patient
    from rdrf.security.security_checks import security_check_user_patient, get_object_or_permission_denied
    from django.core.exceptions import PermissionDenied
    from rdrf.forms.components import FormsButton
    from django.utils.translation import gettext as _

    user = request.user
    fail_response = {"status": "fail", "message": _("Data could not be retrieved")}

    try:
        registry_model = Registry.objects.get(code=registry_code)
    except Registry.DoesNotExist:
        return fail_response

    try:
        patient_model = get_object_or_permission_denied(Patient, pk=patient_id)
    except Patient.DoesNotExist:
        return fail_response

    try:
        security_check_user_patient(user, patient_model)
    except PermissionDenied:
        return fail_response

    if not patient_model.in_registry(registry_model.code):
        return fail_response

    if not user.is_superuser and not user.in_registry(registry_model):
        return fail_response

    if form_group_id is not None:
        try:
            context_form_group = ContextFormGroup.objects.get(id=form_group_id)
        except ContextFormGroup.DoesNotExist:
            logger.debug("cfg does not exist")
            return fail_response
    else:
        context_form_group = None

    forms = context_form_group.forms if context_form_group else registry_model.forms

    form_models = [f for f in forms
                   if f.applicable_to(patient_model) and user.can_view(f)]

    html = FormsButton(registry_model,
                       user,
                       patient_model,
                       context_form_group,
                       form_models).html

    return {"status": "success",
            "html": html}

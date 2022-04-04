import logging

from django.core.exceptions import PermissionDenied

from rdrf.security.security_checks import security_check_user_patient

logger = logging.getLogger(__name__)


def rpc_reporting_command(request, query_id, registry_id, command, arg):
    from rdrf.helpers.registry_features import RegistryFeatures
    from rdrf.models.definition.models import Registry
    if not any(r.has_feature(RegistryFeatures.LEGACY_REPORTS) for r in Registry.objects.all()):
        raise Exception('Explorer reports not enabled')

    # 2 possible commands/invocations client side from report definition screen:
    # get_field_data: used to build all the checkboxes for client
    # get_projection: process the checked checkboxes and get json representation
    # of the selected mongo fields ( used to build temp table)
    from rdrf.services.io.reporting.reporting_table import MongoFieldSelector
    from rdrf.models.definition.models import Registry
    from explorer.models import Query
    user = request.user

    if query_id == "new":
        query_model = None
    else:
        query_model = Query.objects.get(pk=int(query_id))
        if not Query.objects.reports_for_user(user).filter(pk=query_id).exists():
            raise PermissionDenied("Report not available for user")

    registry_model = Registry.objects.get(pk=int(registry_id))
    if not user.in_registry(registry_model):
        raise PermissionDenied("User not a member of this registry")

    if command == "get_projection":
        checkbox_ids = arg["checkbox_ids"]
        longitudinal_ids = arg['longitudinal_ids']
        field_selector = MongoFieldSelector(
            user,
            registry_model,
            query_model,
            checkbox_ids,
            longitudinal_ids)
        result = field_selector.projections_json
        return result
    elif command == "get_field_data":
        field_selector = MongoFieldSelector(user, registry_model, query_model)
        return field_selector.field_data
    else:
        raise Exception("unknown command: %s" % command)


# questionnaire handling

def rpc_load_matched_patient_data(request, patient_id, questionnaire_response_id):
    """
    Try to return any existing data for a patient corresponding the filled in values
    of a questionnaire filled out by on the questionnaire interface
    NB. The curator is responsible for matching an existing patient to the incoming
    questionnaire data.
    See RDR-1229 for a description of the use case.

    The existing data returned is the existing questionnaire values for this matched patient ( not the data
    provided in the questionnaire response itself - which potentially may overwrite the matched data if
    the curator indicates in the approval GUI.
    """
    from registry.patients.models import Patient
    from rdrf.models.definition.models import QuestionnaireResponse
    from rdrf.workflows.questionnaires.questionnaires import Questionnaire
    from django.utils.translation import ugettext as _

    patient_model = Patient.objects.get(pk=patient_id)
    try:
        security_check_user_patient(request.user, patient_model)
    except PermissionDenied:
        return {"status": "fail", "message": _("Permission error. Data cannot be loaded !")}

    questionnaire_response_model = QuestionnaireResponse.objects.get(
        pk=questionnaire_response_id)
    patient_model = Patient.objects.get(pk=patient_id)
    registry_model = questionnaire_response_model.registry
    questionnaire = Questionnaire(registry_model, questionnaire_response_model)
    existing_data = questionnaire.existing_data(patient_model)

    return {"link": existing_data.link,
            "name": existing_data.name,
            "questions": existing_data.questions}


def rpc_update_selected_cdes_from_questionnaire(
        request,
        patient_id,
        questionnaire_response_id,
        questionnaire_checked_ids):
    from registry.patients.models import Patient
    from rdrf.models.definition.models import QuestionnaireResponse
    from rdrf.workflows.questionnaires.questionnaires import Questionnaire
    from django.db import transaction
    from django.utils.translation import ugettext as _

    patient_model = Patient.objects.get(pk=patient_id)
    try:
        security_check_user_patient(request.user, patient_model)
    except PermissionDenied:
        return {"status": "fail", "message": _("Permission error. Data cannot be updated !")}

    questionnaire_response_model = QuestionnaireResponse.objects.get(
        pk=questionnaire_response_id)
    registry_model = questionnaire_response_model.registry
    questionnaire = Questionnaire(registry_model, questionnaire_response_model)
    data_to_update = [
        question for question in questionnaire.questions if question.src_id in questionnaire_checked_ids]

    try:
        with transaction.atomic():
            errors = questionnaire.update_patient(patient_model, data_to_update)
            if len(errors) > 0:
                raise Exception("Errors occurred during update: %s" % ",".join(errors))
    except Exception as ex:
        logger.error("Update patient failed: rolled back: %s" % ex)
        return {"status": "fail", "message": ",".join(errors)}
    else:
        questionnaire_response_model.processed = True
        questionnaire_response_model.patient_id = patient_model.pk
        questionnaire_response_model.save()
        return {"status": "success", "message": "Patient updated successfully"}


def rpc_create_patient_from_questionnaire(request, questionnaire_response_id):
    from rdrf.models.definition.models import QuestionnaireResponse
    from rdrf.workflows.questionnaires.questionnaires import PatientCreator, PatientCreatorError
    from rdrf.db.dynamic_data import DynamicDataWrapper
    from django.db import transaction
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    if not (request.user.is_superuser or request.user.is_staff):
        return {"status": "fail", "message": _("Permission error. Patient cannot be created!")}

    qr = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)
    patient_creator = PatientCreator(qr.registry, request.user)
    wrapper = DynamicDataWrapper(qr)
    questionnaire_data = wrapper.load_dynamic_data(qr.registry.code, "cdes")
    patient_id = None
    patient_blurb = None
    patient_link = None
    created_patient = "Not Created!"

    try:
        with transaction.atomic():
            created_patient = patient_creator.create_patient(None, qr, questionnaire_data)
            status = "success"
            message = "Patient created successfully"
            patient_blurb = "Patient %s created successfully" % created_patient
            patient_id = created_patient.pk
            patient_link = reverse('patient_edit', args=[qr.registry.code, patient_id])

    except PatientCreatorError as pce:
        message = "Error creating patient: %s.Patient not created" % pce
        status = "fail"

    except Exception as ex:
        message = "Unhandled error during patient creation: %s. Patient not created" % ex
        status = "fail"

    return {"status": status,
            "message": message,
            "patient_id": patient_id,
            "patient_name": "%s" % created_patient,
            "patient_link": patient_link,
            "patient_blurb": patient_blurb}


def rpc_get_forms_list(request, registry_code, patient_id, form_group_id):
    from rdrf.models.definition.models import ContextFormGroup
    from rdrf.models.definition.models import Registry
    from registry.patients.models import Patient
    from rdrf.security.security_checks import security_check_user_patient, get_object_or_permission_denied
    from django.core.exceptions import PermissionDenied
    from rdrf.forms.components import FormsButton
    from django.utils.translation import ugettext as _

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

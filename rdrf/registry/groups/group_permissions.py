import logging

from django.contrib.auth.models import Permission

logger = logging.getLogger(__name__)


def add_permissions_to_group(group, role):
    permissions = []
    for permission_code in PERMISSIONS_BY_ROLES[role]:
        try:
            permissions.append(Permission.objects.get(codename=permission_code))
        except Permission.DoesNotExist:
            logger.warning(
                'Permission "%s" required by role "%s" does NOT exist',
                permission_code,
                role,
            )
    group.permissions.add(*permissions)


# Note: Permissions have been created initially by copying permissions
# from OPHG staging installation
PERMISSIONS_BY_ROLES = {
    # Not sure if we need this
    # 'AdminOnly': [],
    "Clinical Staff": [
        "change_addresstype",
        "delete_addresstype",
        "add_nextofkinrelationship",
        "change_nextofkinrelationship",
        "delete_nextofkinrelationship",
        "add_patient",
        "can_see_data_modules",
        "can_see_diagnosis_currency",
        "can_see_diagnosis_progress",
        "can_see_dob",
        "can_see_full_name",
        "can_see_working_groups",
        "change_patient",
        "delete_patient",
        "add_patientaddress",
        "change_patientaddress",
        "delete_patientaddress",
        "add_patientconsent",
        "change_patientconsent",
        "delete_patientconsent",
        "add_patientrelative",
        "change_patientrelative",
        "delete_patientrelative",
        "add_state",
        "change_state",
        "delete_state",
        "can_run_reports",
    ],
    "Parents": [],
    "Patients": [],
    "Carer": [
        "can_see_code_field",
        "can_see_data_modules",
        "can_see_diagnosis_currency",
        "can_see_diagnosis_progress",
        "can_see_dob",
        "can_see_full_name",
        "can_see_working_groups",
        "view_patient",
    ],
    "Working Group Curators": [
        "add_addresstype",
        "change_addresstype",
        "delete_addresstype",
        "add_doctor",
        "change_doctor",
        "delete_doctor",
        "add_nextofkinrelationship",
        "change_nextofkinrelationship",
        "delete_nextofkinrelationship",
        "add_patient",
        "can_see_data_modules",
        "can_see_dob",
        "can_see_full_name",
        "can_see_working_groups",
        "change_patient",
        "delete_patient",
        "add_patientaddress",
        "change_patientaddress",
        "delete_patientaddress",
        "add_patientconsent",
        "change_patientconsent",
        "delete_patientconsent",
        "add_patientdoctor",
        "change_patientdoctor",
        "delete_patientdoctor",
        "add_patientrelative",
        "change_patientrelative",
        "delete_patientrelative",
        "add_state",
        "change_state",
        "delete_state",
        "can_run_reports",
    ],
    "Working Group Staff": [
        "add_addresstype",
        "change_addresstype",
        "delete_addresstype",
        "add_consentvalue",
        "change_consentvalue",
        "delete_consentvalue",
        "add_nextofkinrelationship",
        "change_nextofkinrelationship",
        "delete_nextofkinrelationship",
        "add_parentguardian",
        "change_parentguardian",
        "delete_parentguardian",
        "add_patient",
        "can_see_data_modules",
        "can_see_diagnosis_currency",
        "can_see_diagnosis_progress",
        "can_see_dob",
        "can_see_full_name",
        "can_see_working_groups",
        "change_patient",
        "delete_patient",
        "add_patientaddress",
        "change_patientaddress",
        "delete_patientaddress",
        "add_patientconsent",
        "change_patientconsent",
        "delete_patientconsent",
        "add_patientrelative",
        "change_patientrelative",
        "delete_patientrelative",
        "add_state",
        "change_state",
        "delete_state",
        "can_run_reports",
    ],
}

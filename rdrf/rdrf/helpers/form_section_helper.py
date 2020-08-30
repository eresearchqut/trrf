from django.utils.translation import ugettext as _

from .constants import (
    PATIENT_ADDRESS_SECTION_NAME, PATIENT_DOCTOR_SECTION_NAME,
    PATIENT_NEXT_OF_KIN_SECTION_NAME, PATIENT_STAGE_SECTION_NAME,
    PATIENT_PERSONAL_DETAILS_SECTION_NAME, PATIENT_RELATIVE_SECTION_NAME
)


class DemographicsSectionFieldBuilder(object):

    def get_personal_detail_fields(self, registry_code):
        personal_header = _(PATIENT_PERSONAL_DETAILS_SECTION_NAME)
        # shouldn't be hardcoding behaviour here plus the html formatting
        # originally here was not being passed as text
        if registry_code == "fkrp":
            personal_header += " " + \
                _("Here you can find an overview of all your personal and contact details you have given us. You can update your contact details by changing the information below.")

        personal_fields = [
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
            "date_of_death",
            "place_of_birth",
            "date_of_migration",
            "country_of_birth",
            "ethnic_origin",
            "sex",
            "home_phone",
            "mobile_phone",
            "work_phone",
            "email",
            "living_status",
        ]
        return (personal_header, personal_fields)

    def get_next_of_kin_fields(self):
        next_of_kin_fields = [
            "next_of_kin_family_name",
            "next_of_kin_given_names",
            "next_of_kin_relationship",
            "next_of_kin_address",
            "next_of_kin_suburb",
            "next_of_kin_country",
            "next_of_kin_state",
            "next_of_kin_postcode",
            "next_of_kin_home_phone",
            "next_of_kin_mobile_phone",
            "next_of_kin_work_phone",
            "next_of_kin_email",
            "next_of_kin_parent_place_of_birth"
        ]
        return (_(PATIENT_NEXT_OF_KIN_SECTION_NAME), next_of_kin_fields)

    def get_registry_fields(self):
        return _("Registry"), ["rdrf_registry", "working_groups", "clinician"]

    def get_patient_address_section(self):
        return _(PATIENT_ADDRESS_SECTION_NAME), None

    def get_patient_stage_section(self):
        return _(PATIENT_STAGE_SECTION_NAME), ["stage"]

    def get_patient_doctor_section(self):
        return _(PATIENT_DOCTOR_SECTION_NAME), None

    def get_patient_relative_section(self):
        return _(PATIENT_RELATIVE_SECTION_NAME), None

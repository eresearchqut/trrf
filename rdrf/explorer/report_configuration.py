from registry.patients.models import Patient, ConsentValue, PatientAddress

REPORT_CONFIGURATION = {
    "models": (Patient, ConsentValue, PatientAddress),
    "demographic_model":
         {"patient":
             {'Id': 'id',
              'Consent': 'consent',
              'Consent Clinical Trials': 'consent_clinical_trials',
              'Consent Sent Information': 'consent_sent_information',
              'Consent Provided By Parent Guardian': 'consent_provided_by_parent_guardian',
              'Family Name': 'family_name',
              'Given Names': 'given_names',
              'Maiden Name': 'maiden_name',
              'Umrn': 'umrn',
              'Date Of Birth': 'date_of_birth',
              'Date Of Death': 'date_of_death',
              'Place Of Birth': 'place_of_birth',
              'Date Of Migration': 'date_of_migration',
              'Country Of Birth': 'country_of_birth',
              'Ethnic Origin': 'ethnic_origin',
              'Sex': 'sex',
              'Home Phone': 'home_phone',
              'Mobile Phone': 'mobile_phone',
              'Work Phone': 'work_phone',
              'Email': 'email',
              'Next Of Kin Family Name': 'next_of_kin_family_name',
              'Next Of Kin Given Names': 'next_of_kin_given_names',
              'Next Of Kin Relationship': 'next_of_kin_relationship',
              'Next Of Kin Address': 'next_of_kin_address',
              'Next Of Kin Suburb': 'next_of_kin_suburb',
              'Next Of Kin State': 'next_of_kin_state',
              'Next Of Kin Postcode': 'next_of_kin_postcode',
              'Next Of Kin Home Phone': 'next_of_kin_home_phone',
              'Next Of Kin Mobile Phone': 'next_of_kin_mobile_phone',
              'Next Of Kin Work Phone': 'next_of_kin_work_phone',
              'Next Of Kin Email': 'next_of_kin_email',
              'Next Of Kin Parent Place Of Birth': 'next_of_kin_parent_place_of_birth',
              'Next Of Kin Country': 'next_of_kin_country',
              'Active': 'active',
              'Inactive Reason': 'inactive_reason',
              'User': 'user',
              'Carer': 'carer',
              'Living Status': 'living_status',
              'Patient Type': 'patient_type',
              'Stage': 'stage',
              'Created At': 'created_at',
              'Last Updated At': 'last_updated_at',
              'Last Updated Overall At': 'last_updated_overall_at',
              'Created By': 'created_by'},
         "Patient Address":
             {'Address Type': 'patientaddress__address_type__type',
              'Street Address': 'patientaddress__address',
              'Suburb': 'patientaddress__suburb'},
         "Working Groups":
             {'Working groups': 'working_groups__name'}}
}
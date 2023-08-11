from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry, EmailNotification


def get_configuration():
    all_registries = Registry.objects.all()

    def get_patient_fields():
        patient_fields_dict = {'id': 'ID'}

        if any(r.has_feature(RegistryFeatures.PATIENT_GUID) for r in all_registries):
            patient_fields_dict.update({'patientguid {guid}': 'GUID'})

        patient_fields_dict.update({
            'familyName': 'Family Name',
            'givenNames': 'Given Names',
            'maidenName': 'Maiden Name',
            'umrn': 'Umrn',
            'createdAt': "Date And Time Of Creation",
            'lastUpdatedOverallAt': 'Date and Time Last Updated',
            'dateOfBirth': 'Date Of Birth',
            'dateOfDeath': 'Date Of Death',
            'placeOfBirth': 'Place Of Birth',
            'dateOfMigration': 'Date Of Migration',
            'countryOfBirth': 'Country Of Birth',
            'ethnicOrigin': 'Ethnic Origin',
            'sex': 'Sex',
            'homePhone': 'Home Phone',
            'mobilePhone': 'Mobile Phone',
            'workPhone': 'Work Phone',
            'email': 'Email',
            'nextOfKinFamilyName': 'Next Of Kin Family Name',
            'nextOfKinGivenNames': 'Next Of Kin Given Names',
            'nextOfKinRelationship { relationship }': 'Next Of Kin Relationship',
            'nextOfKinAddress': 'Next Of Kin Address',
            'nextOfKinSuburb': 'Next Of Kin Suburb',
            'nextOfKinState': 'Next Of Kin State',
            'nextOfKinPostcode': 'Next Of Kin Postcode',
            'nextOfKinHomePhone': 'Next Of Kin Home Phone',
            'nextOfKinMobilePhone': 'Next Of Kin Mobile Phone',
            'nextOfKinWorkPhone': 'Next Of Kin Work Phone',
            'nextOfKinEmail': 'Next Of Kin Email',
            'nextOfKinParentPlaceOfBirth': 'Next Of Kin Parent Place Of Birth',
            'nextOfKinCountry': 'Next Of Kin Country',
            'inactiveReason': 'Inactive Reason',
            'livingStatus': 'Living Status',
            'patientType': 'Patient Type'
        })

        return patient_fields_dict

    demographic_model = {
        'demographic_model': {
            'patient': {
                'label': "Patient",
                'fields': get_patient_fields()
            },
            'patientaddressSet': {
                'label': 'Patient Address',
                'multi_field': True,
                'variant_lookup': 'maxAddressCount',
                'fields': {
                    'addressType { type }': 'Address Type',
                    'address': 'Street Address',
                    'suburb': 'Suburb',
                    'state': 'State',
                    'postcode': 'Postcode',
                    'country': 'Country'}},
            'workingGroups': {
                'label': 'Working Groups',
                'multi_field': True,
                'variant_lookup': 'maxWorkingGroupCount',
                'fields': {
                    'displayName': 'Name',
                    'type { name }': 'Type'
                }
            },
            'registeredClinicians': {
                'label': 'Registered Clinicians',
                'multi_field': True,
                'variant_lookup': 'maxClinicianCount',
                'fields': {
                    'firstName': 'First Name',
                    'lastName': 'Last Name',
                    'email': 'Email',
                    'ethicallyCleared': 'Ethically Cleared',
                    'workingGroups': 'Working Groups'
                }
            },
            'consents': {
                'label': 'Consents',
                'multi_field': True,
                'pivot': True,
                'variant_lookup': 'listConsentQuestionCodes',
                'fields': {
                    'answer': 'Answer',
                    'firstSave': 'Date of First Save',
                    'lastUpdate': 'Date of Last Update'
                }
            },
            'parentguardianSet': {
                'label': 'Parent / Guardian',
                'multi_field': True,
                'variant_lookup': 'maxParentGuardianCount',
                'fields': {
                    'firstName': 'First Name',
                    'lastName': 'Last Name',
                    'dateOfBirth': 'Date of Birth',
                    'placeOfBirth': 'Place of Birth',
                    'dateOfMigration': 'Date of Migration',
                    'gender': 'Gender',
                    'address': 'Address',
                    'suburb': 'Suburb',
                    'state': 'State',
                    'postcode': 'Postcode',
                    'country': 'Country',
                    'phone': 'Phone',
                    'email': 'Email',
                    'selfPatientId': 'Self Patient ID'
                }
            },

        }
    }

    if EmailNotification.objects.has_subscribable_registry(all_registries):
        demographic_model['demographic_model'].update({
            'emailNotifications': {
                'label': 'Email Notifications',
                'fields': {
                    'unsubscribeAll': 'Unsubscribe All'
                }
            }
        })

    return demographic_model

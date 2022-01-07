REPORT_CONFIGURATION = {
    'demographic_model':
       {'patient': {
             'label': "Patient",
             'fields': {
                  'Consent': 'consent',
                  'Consent Clinical Trials': 'consentClinicalTrials',
                  'Consent Sent Information': 'consentSentInformation',
                  'Consent Provided By Parent Guardian': 'consentProvidedByParentGuardian',
                  'Family Name': 'familyName',
                  'Given Names': 'givenNames',
                  'Maiden Name': 'maidenName',
                  'Umrn': 'umrn',
                  'Date Of Birth': 'dateOfBirth',
                  'Date Of Death': 'dateOfDeath',
                  'Place Of Birth': 'placeOfBirth',
                  'Date Of Migration': 'dateOfMigration',
                  'Country Of Birth': 'countryOfBirth',
                  'Ethnic Origin': 'ethnicOrigin',
                  'Sex': 'sex',
                  'Home Phone': 'homePhone',
                  'Mobile Phone': 'mobilePhone',
                  'Work Phone': 'workPhone',
                  'Email': 'email',
                  'Next Of Kin Family Name': 'nextOfKinFamilyName',
                  'Next Of Kin Given Names': 'nextOfKinGivenNames',
                  'Next Of Kin Relationship': 'nextOfKinRelationship { relationship }',
                  'Next Of Kin Address': 'nextOfKinAddress',
                  'Next Of Kin Suburb': 'nextOfKinSuburb',
                  'Next Of Kin State': 'nextOfKinState',
                  'Next Of Kin Postcode': 'nextOfKinPostcode',
                  'Next Of Kin Home Phone': 'nextOfKinHomePhone',
                  'Next Of Kin Mobile Phone': 'nextOfKinMobilePhone',
                  'Next Of Kin Work Phone': 'nextOfKinWorkPhone',
                  'Next Of Kin Email': 'nextOfKinEmail',
                  'Next Of Kin Parent Place Of Birth': 'nextOfKinParentPlaceOfBirth',
                  'Next Of Kin Country': 'nextOfKinCountry',
                  'Inactive Reason': 'inactiveReason',
                  'Living Status': 'livingStatus',
                  'Patient Type': 'patientType'}},
         "patientaddressSet": {
              'label': 'Patient Address',
              'pivot_field': 'addressType { type }',
              'fields': {
                  'Address Type': 'addressType { type }',
                  'Street Address': 'address',
                  'Suburb': 'suburb',
                  'State': 'state',
                  'Postcode': 'postcode',
                  'Country': 'country'}},
         "workingGroups": {
              'label': 'Working Groups',
              'pivot_field': 'name',
              'fields': {
                  'Name': 'displayName'
              }
         }
    }
}
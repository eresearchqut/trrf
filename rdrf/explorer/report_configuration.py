REPORT_CONFIGURATION = {
    'demographic_model':
       {'patient': {
             'label': "Patient",
             'fields': {
                  'consent': 'Consent',
                  'consentClinicalTrials': 'Consent Clinical Trials',
                  'consentSentInformation': 'Consent Sent Information',
                  'consentProvidedByParentGuardian': 'Consent Provided By Parent Guardian',
                  'familyName': 'Family Name',
                  'givenNames': 'Given Names',
                  'maidenName': 'Maiden Name',
                  'umrn': 'Umrn',
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
                  'patientType': 'Patient Type'}},
         "patientaddressSet": {
              'label': 'Patient Address',
              'pivot_field': 'addressType { type }',
              'fields': {
                  'addressType { type }': 'Address Type',
                  'address': 'Street Address',
                  'suburb': 'Suburb',
                  'state': 'State',
                  'postcode': 'Postcode',
                  'country': 'Country'}},
         "workingGroups": {
              'label': 'Working Groups',
              'pivot_field': 'name',
              'fields': {
                  'displayName': 'Name'
              }
         }
    }
}
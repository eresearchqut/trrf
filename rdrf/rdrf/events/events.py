class EventType:
    OTHER_CLINICIAN = "other-clinician"
    NEW_PATIENT_USER_REGISTERED = "new-patient-user-registered"
    NEW_PATIENT_PARENT = "new-patient-parent"
    NEW_PATIENT_USER_ADDED = "new-patient-user-added"
    ACCOUNT_LOCKED = "account-locked"
    ACCOUNT_VERIFIED = "account-verified"
    PASSWORD_EXPIRY_WARNING = "password-expiry-warning"
    REMINDER = "reminder"
    CLINICIAN_SELECTED = "clinician-selected"  # existing clinician selected by patient as their clinician
    CLINICIAN_SIGNUP_REQUEST = "clinician-signup-request"  # clinician email to sign up
    CLINICIAN_ACTIVATION = "clinician-activation"  # clinician email to confirm registration
    PARTICIPANT_CLINICIAN_NOTIFICATION = "participant-clinician-notification"  # participant (parent) notified when clinician verifies
    PATIENT_CONSENT_CHANGE = "patient-consent-change"   # clinician is notified of a patient changing consent values
    NEW_CARER = "new-carer"
    CARER_INVITED = "carer-invited"
    CARER_ASSIGNED = "carer-assigned"
    CARER_ACTIVATED = "carer-activated"
    CARER_DEACTIVATED = "carer-deactivated"
    DUPLICATE_PATIENT_SET = "duplicate-patient-set"
    CLINICIAN_ASSIGNED = "clinician-assigned"
    CLINICIAN_UNASSIGNED = "clinician-unassigned"
    FILE_UPLOADED = "file-uploaded"
    LONGITUDINAL_FOLLOWUP = "longitudinal-followup"
    EMAIL_CHANGE_REQUEST = "email-change-request"
    EMAIL_CHANGE_COMPLETE = "email-change-complete"

    REGISTRATION_TYPES = [NEW_PATIENT_USER_REGISTERED, NEW_PATIENT_PARENT]
    CARER_REGISTRATION_TYPES = [NEW_CARER, CARER_INVITED]

    @classmethod
    def is_registration(cls, evt):
        return evt in cls.REGISTRATION_TYPES

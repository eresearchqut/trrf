class EventType:
    OTHER_CLINICIAN = "other-clinician"
    NEW_PATIENT = "new-patient"
    NEW_PATIENT_PARENT = "new-patient-parent"
    ACCOUNT_LOCKED = "account-locked"
    ACCOUNT_VERIFIED = "account-verified"
    PASSWORD_EXPIRY_WARNING = "password-expiry-warning"
    REMINDER = "reminder"

    # existing clinician selected by patient as their clinician
    CLINICIAN_SELECTED = "clinician-selected"
    # clinican email to sign up
    CLINICIAN_SIGNUP_REQUEST = "clinician-signup-request"
    # clinican email to confirm registration
    CLINICIAN_ACTIVATION = "clinician-activation"
    # participant (parent) notified when clinician verifies
    PARTICIPANT_CLINICIAN_NOTIFICATION = "participant-clinician-notification"
    # clinician is notified of a patient changing consent values
    PATIENT_CONSENT_CHANGE = "patient-consent-change"

    REGISTRATION_TYPES = [NEW_PATIENT, NEW_PATIENT_PARENT]

    @classmethod
    def is_registration(cls, evt):
        return evt in cls.REGISTRATION_TYPES

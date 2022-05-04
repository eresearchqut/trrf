SECURITY_WHITELISTED_URLS = (
    "action",
    "admin:app_list",
    "admin:auth_group_add",
    "admin:auth_group_autocomplete",
    "admin:auth_group_change",
    "admin:auth_group_changelist",
    "admin:auth_group_delete",
    "admin:auth_group_history",
    "admin:auth_user_password_change",
    "admin:authtoken_token_add",
    "admin:authtoken_token_autocomplete",
    "admin:authtoken_token_change",
    "admin:authtoken_token_changelist",
    "admin:authtoken_token_delete",
    "admin:authtoken_token_history",
    "admin:explorer_query_add",
    "admin:explorer_query_autocomplete",
    "admin:explorer_query_change",
    "admin:explorer_query_changelist",
    "admin:explorer_query_delete",
    "admin:explorer_query_history",
    "admin:groups_customuser_add",
    "admin:groups_customuser_autocomplete",
    "admin:groups_customuser_change",
    "admin:groups_customuser_changelist",
    "admin:groups_customuser_delete",
    "admin:groups_customuser_history",
    "admin:groups_workinggroup_add",
    "admin:groups_workinggroup_autocomplete",
    "admin:groups_workinggroup_change",
    "admin:groups_workinggroup_changelist",
    "admin:groups_workinggroup_delete",
    "admin:groups_workinggroup_history",
    "admin:index",
    "admin:jsi18n",
    "admin:login",
    "admin:logout",
    "admin:otp_static_staticdevice_add",
    "admin:otp_static_staticdevice_autocomplete",
    "admin:otp_static_staticdevice_change",
    "admin:otp_static_staticdevice_changelist",
    "admin:otp_static_staticdevice_delete",
    "admin:otp_static_staticdevice_history",
    "admin:otp_totp_totpdevice_add",
    "admin:otp_totp_totpdevice_autocomplete",
    "admin:otp_totp_totpdevice_change",
    "admin:otp_totp_totpdevice_changelist",
    "admin:otp_totp_totpdevice_config",
    "admin:otp_totp_totpdevice_delete",
    "admin:otp_totp_totpdevice_history",
    "admin:otp_totp_totpdevice_qrcode",
    "admin:password_change",
    "admin:password_change_done",
    "admin:patient_search",
    "admin:patients_addresstype_add",
    "admin:patients_addresstype_autocomplete",
    "admin:patients_addresstype_change",
    "admin:patients_addresstype_changelist",
    "admin:patients_addresstype_delete",
    "admin:patients_addresstype_history",
    "admin:patients_archivedpatient_add",
    "admin:patients_archivedpatient_autocomplete",
    "admin:patients_archivedpatient_change",
    "admin:patients_archivedpatient_changelist",
    "admin:patients_archivedpatient_delete",
    "admin:patients_archivedpatient_history",
    "admin:patients_clinicianother_add",
    "admin:patients_clinicianother_autocomplete",
    "admin:patients_clinicianother_change",
    "admin:patients_clinicianother_changelist",
    "admin:patients_clinicianother_delete",
    "admin:patients_clinicianother_history",
    "admin:patients_consentvalue_add",
    "admin:patients_consentvalue_autocomplete",
    "admin:patients_consentvalue_change",
    "admin:patients_consentvalue_changelist",
    "admin:patients_consentvalue_delete",
    "admin:patients_consentvalue_history",
    "admin:patients_doctor_add",
    "admin:patients_doctor_autocomplete",
    "admin:patients_doctor_change",
    "admin:patients_doctor_changelist",
    "admin:patients_doctor_delete",
    "admin:patients_doctor_history",
    "admin:patients_nextofkinrelationship_add",
    "admin:patients_nextofkinrelationship_autocomplete",
    "admin:patients_nextofkinrelationship_change",
    "admin:patients_nextofkinrelationship_changelist",
    "admin:patients_nextofkinrelationship_delete",
    "admin:patients_nextofkinrelationship_history",
    "admin:patients_parentguardian_add",
    "admin:patients_parentguardian_autocomplete",
    "admin:patients_parentguardian_change",
    "admin:patients_parentguardian_changelist",
    "admin:patients_parentguardian_delete",
    "admin:patients_parentguardian_history",
    "admin:patients_patient_add",
    "admin:patients_patient_autocomplete",
    "admin:patients_patient_change",
    "admin:patients_patient_changelist",
    "admin:patients_patient_delete",
    "admin:patients_patient_history",
    "admin:patients_patientstage_add",
    "admin:patients_patientstage_autocomplete",
    "admin:patients_patientstage_change",
    "admin:patients_patientstage_changelist",
    "admin:patients_patientstage_delete",
    "admin:patients_patientstage_history",
    "admin:patients_patientstagerule_add",
    "admin:patients_patientstagerule_autocomplete",
    "admin:patients_patientstagerule_change",
    "admin:patients_patientstagerule_changelist",
    "admin:patients_patientstagerule_delete",
    "admin:patients_patientstagerule_history",
    "admin:patients_state_add",
    "admin:patients_state_autocomplete",
    "admin:patients_state_change",
    "admin:patients_state_changelist",
    "admin:patients_state_delete",
    "admin:patients_state_history",
    "admin:rdrf_blacklistedmimetype_add",
    "admin:rdrf_blacklistedmimetype_autocomplete",
    "admin:rdrf_blacklistedmimetype_change",
    "admin:rdrf_blacklistedmimetype_changelist",
    "admin:rdrf_blacklistedmimetype_delete",
    "admin:rdrf_blacklistedmimetype_history",
    "admin:rdrf_cdefile_add",
    "admin:rdrf_cdefile_autocomplete",
    "admin:rdrf_cdefile_change",
    "admin:rdrf_cdefile_changelist",
    "admin:rdrf_cdefile_delete",
    "admin:rdrf_cdefile_history",
    "admin:rdrf_cdepermittedvalue_add",
    "admin:rdrf_cdepermittedvalue_autocomplete",
    "admin:rdrf_cdepermittedvalue_change",
    "admin:rdrf_cdepermittedvalue_changelist",
    "admin:rdrf_cdepermittedvalue_delete",
    "admin:rdrf_cdepermittedvalue_history",
    "admin:rdrf_cdepermittedvaluegroup_add",
    "admin:rdrf_cdepermittedvaluegroup_autocomplete",
    "admin:rdrf_cdepermittedvaluegroup_change",
    "admin:rdrf_cdepermittedvaluegroup_changelist",
    "admin:rdrf_cdepermittedvaluegroup_delete",
    "admin:rdrf_cdepermittedvaluegroup_history",
    "admin:rdrf_cdepolicy_add",
    "admin:rdrf_cdepolicy_autocomplete",
    "admin:rdrf_cdepolicy_change",
    "admin:rdrf_cdepolicy_changelist",
    "admin:rdrf_cdepolicy_delete",
    "admin:rdrf_cdepolicy_history",
    "admin:rdrf_clinicaldata_add",
    "admin:rdrf_clinicaldata_autocomplete",
    "admin:rdrf_clinicaldata_change",
    "admin:rdrf_clinicaldata_changelist",
    "admin:rdrf_clinicaldata_delete",
    "admin:rdrf_clinicaldata_history",
    "admin:rdrf_clinicaldata_recover",
    "admin:rdrf_clinicaldata_recoverlist",
    "admin:rdrf_clinicaldata_revision",
    "admin:rdrf_commondataelement_add",
    "admin:rdrf_commondataelement_autocomplete",
    "admin:rdrf_commondataelement_change",
    "admin:rdrf_commondataelement_changelist",
    "admin:rdrf_commondataelement_delete",
    "admin:rdrf_commondataelement_history",
    "admin:rdrf_consentconfiguration_add",
    "admin:rdrf_consentconfiguration_autocomplete",
    "admin:rdrf_consentconfiguration_change",
    "admin:rdrf_consentconfiguration_changelist",
    "admin:rdrf_consentconfiguration_delete",
    "admin:rdrf_consentconfiguration_history",
    "admin:rdrf_consentrule_add",
    "admin:rdrf_consentrule_autocomplete",
    "admin:rdrf_consentrule_change",
    "admin:rdrf_consentrule_changelist",
    "admin:rdrf_consentrule_delete",
    "admin:rdrf_consentrule_history",
    "admin:rdrf_consentsection_add",
    "admin:rdrf_consentsection_autocomplete",
    "admin:rdrf_consentsection_change",
    "admin:rdrf_consentsection_changelist",
    "admin:rdrf_consentsection_delete",
    "admin:rdrf_consentsection_history",
    "admin:rdrf_contextformgroup_add",
    "admin:rdrf_contextformgroup_autocomplete",
    "admin:rdrf_contextformgroup_change",
    "admin:rdrf_contextformgroup_changelist",
    "admin:rdrf_contextformgroup_delete",
    "admin:rdrf_contextformgroup_history",
    "admin:rdrf_demographicfields_add",
    "admin:rdrf_demographicfields_autocomplete",
    "admin:rdrf_demographicfields_change",
    "admin:rdrf_demographicfields_changelist",
    "admin:rdrf_demographicfields_delete",
    "admin:rdrf_demographicfields_history",
    "admin:rdrf_emailnotification_add",
    "admin:rdrf_emailnotification_autocomplete",
    "admin:rdrf_emailnotification_change",
    "admin:rdrf_emailnotification_changelist",
    "admin:rdrf_emailnotification_delete",
    "admin:rdrf_emailnotification_history",
    "admin:rdrf_emailnotificationhistory_add",
    "admin:rdrf_emailnotificationhistory_autocomplete",
    "admin:rdrf_emailnotificationhistory_change",
    "admin:rdrf_emailnotificationhistory_changelist",
    "admin:rdrf_emailnotificationhistory_delete",
    "admin:rdrf_emailnotificationhistory_history",
    "admin:rdrf_emailtemplate_add",
    "admin:rdrf_emailtemplate_autocomplete",
    "admin:rdrf_emailtemplate_change",
    "admin:rdrf_emailtemplate_changelist",
    "admin:rdrf_emailtemplate_delete",
    "admin:rdrf_emailtemplate_history",
    "admin:rdrf_formtitle_add",
    "admin:rdrf_formtitle_autocomplete",
    "admin:rdrf_formtitle_change",
    "admin:rdrf_formtitle_changelist",
    "admin:rdrf_formtitle_delete",
    "admin:rdrf_formtitle_history",
    "admin:rdrf_notification_add",
    "admin:rdrf_notification_autocomplete",
    "admin:rdrf_notification_change",
    "admin:rdrf_notification_changelist",
    "admin:rdrf_notification_delete",
    "admin:rdrf_notification_history",
    "admin:rdrf_precondition_add",
    "admin:rdrf_precondition_autocomplete",
    "admin:rdrf_precondition_change",
    "admin:rdrf_precondition_changelist",
    "admin:rdrf_precondition_delete",
    "admin:rdrf_precondition_history",
    "admin:rdrf_questionnaireresponse_add",
    "admin:rdrf_questionnaireresponse_autocomplete",
    "admin:rdrf_questionnaireresponse_change",
    "admin:rdrf_questionnaireresponse_changelist",
    "admin:rdrf_questionnaireresponse_delete",
    "admin:rdrf_questionnaireresponse_history",
    "admin:rdrf_registry_add",
    "admin:rdrf_registry_autocomplete",
    "admin:rdrf_registry_change",
    "admin:rdrf_registry_changelist",
    "admin:rdrf_registry_delete",
    "admin:rdrf_registry_history",
    "admin:rdrf_registryform_add",
    "admin:rdrf_registryform_autocomplete",
    "admin:rdrf_registryform_change",
    "admin:rdrf_registryform_changelist",
    "admin:rdrf_registryform_delete",
    "admin:rdrf_registryform_history",
    "admin:rdrf_section_add",
    "admin:rdrf_section_autocomplete",
    "admin:rdrf_section_change",
    "admin:rdrf_section_changelist",
    "admin:rdrf_section_delete",
    "admin:rdrf_section_history",
    "admin:registration_registrationprofile_add",
    "admin:registration_registrationprofile_autocomplete",
    "admin:registration_registrationprofile_change",
    "admin:registration_registrationprofile_changelist",
    "admin:registration_registrationprofile_delete",
    "admin:registration_registrationprofile_history",
    "admin:sites_site_add",
    "admin:sites_site_autocomplete",
    "admin:sites_site_change",
    "admin:sites_site_changelist",
    "admin:sites_site_delete",
    "admin:sites_site_history",
    "admin:two_factor_phonedevice_add",
    "admin:two_factor_phonedevice_autocomplete",
    "admin:two_factor_phonedevice_change",
    "admin:two_factor_phonedevice_changelist",
    "admin:two_factor_phonedevice_delete",
    "admin:two_factor_phonedevice_history",
    "admin:useraudit_failedloginlog_add",
    "admin:useraudit_failedloginlog_autocomplete",
    "admin:useraudit_failedloginlog_change",
    "admin:useraudit_failedloginlog_changelist",
    "admin:useraudit_failedloginlog_delete",
    "admin:useraudit_failedloginlog_history",
    "admin:useraudit_loginattempt_add",
    "admin:useraudit_loginattempt_autocomplete",
    "admin:useraudit_loginattempt_change",
    "admin:useraudit_loginattempt_changelist",
    "admin:useraudit_loginattempt_delete",
    "admin:useraudit_loginattempt_history",
    "admin:useraudit_loginlog_add",
    "admin:useraudit_loginlog_autocomplete",
    "admin:useraudit_loginlog_change",
    "admin:useraudit_loginlog_changelist",
    "admin:useraudit_loginlog_delete",
    "admin:useraudit_loginlog_history",
    "admin:view_on_site",
    "ajax_select_urls:ajax_lookup",
    "cde_available_widgets",
    "cde_widget_settings",
    "clinician_activate",
    "clinician_form_view",
    "consent_details",
    "consent_form_view",
    "consent_list",
    "context_add",
    "context_edit",
    "copyright",
    "django_conf_urls:set_language",
    "family_linkage",
    "favicon",
    "file_upload",
    "form_add",
    "health_check",
    "import_registry",
    "javascript-catalog",
    "js_reverse",
    "landing",
    "login_assistance",
    "login_assistance_complete",
    "login_assistance_confirm",
    "login_assistance_email_sent",
    "login_router",
    "logout",
    "password_change",
    "password_change_done",
    "password_reset",
    "password_reset_complete",
    "password_reset_confirm",
    "password_reset_done",
    "patient_add",
    "patient_edit",
    "patient_lookup",
    "patient_verification",
    "patientslisting",
    "permission_matrix",
    "print_consent_list",
    "questionnaire",
    "questionnaire_config",
    "questionnaire_response",
    "rdrf:explorer_main",
    "rdrf:explorer_new",
    "rdrf:explorer_query",
    "rdrf:explorer_query_delete",
    "rdrf:explorer_query_download",
    "rdrf:explorer_sql_query",
    "report:report_designer",
    "report:report_download",
    "report:report_delete",
    "report:reports_list",
    "registration_activate",
    "registration_activation_complete",
    "registration_complete",
    "registration_disallowed",
    "registration_failed",
    "registration_register",
    "registry",
    "registry:consent-form-download",
    "registry:parent_edit",
    "registry:parent_page",
    "registry:patient_page",
    "registry_form",
    "registry_form_dsl_help",
    "registry_form_field_history",
    "registry_form_list",
    "report_datatable",
    "reports",
    "resend_email",
    "robots_txt",
    "rpc",
    "session_refresh",
    "test 404",
    "test 500",
    "test application error",
    "test exception",
    "two_factor:disable",
    "two_factor:login",
    "two_factor:qr",
    "two_factor:setup",
    "two_factor:setup_complete",
    "useraudit:reactivate_user",
    "v1:api-root",
    "v1:api-root",
    "v1:country-list",
    "v1:customuser-detail",
    "v1:customuser-detail",
    "v1:customuser-list",
    "v1:customuser-list",
    "v1:nextofkinrelationship-detail",
    "v1:nextofkinrelationship-list",
    "v1:patient-detail",
    "v1:patient-list",
    "v1:patient-stages",
    "v1:registry-forms",
    "v1:state_lookup",
    "verifications_list",
)

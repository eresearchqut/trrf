import logging
from collections import namedtuple
from functools import reduce
from operator import attrgetter

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, reverse_lazy
from django.urls.exceptions import NoReverseMatch
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from registry import groups
from registry.groups import GROUPS as RDRF_GROUPS
from report.models import ReportDesign

from rdrf.helpers.registry_features import RegistryFeatures

logger = logging.getLogger(__name__)


QuickLink = namedtuple("QuickLink", "url text")


def make_entries(*quick_links):
    return {link.text: link for link in quick_links}


def make_link(url, text):
    return QuickLink(reverse_lazy(url), text)


class LinkDefs:
    Doctors = make_link("admin:patients_doctor_changelist", _("Doctors"))
    ArchivedPatients = make_link(
        "admin:patients_archivedpatient_changelist", _("Archived Patients")
    )
    PatientStages = make_link(
        "admin:patients_patientstage_changelist", _("Patient Stages")
    )
    PatientStageRules = make_link(
        "admin:patients_patientstagerule_changelist", _("Patient Stages Rules")
    )
    PatientUser = QuickLink(
        f'{reverse("admin:patients_patientuser_changelist")}?{urlencode({"linked": "N"})}',
        _("Patient Users"),
    )
    Reports = make_link("report:reports_list", _("Reports"))
    Users = make_link("admin:groups_customuser_changelist", _("Users"))
    WorkingGroups = make_link(
        "admin:groups_workinggroup_changelist", _("Working Groups")
    )
    WorkingGroupTypes = make_link(
        "admin:groups_workinggrouptype_changelist", _("Working Group Types")
    )
    Registries = make_link("admin:rdrf_registry_changelist", _("Registries"))
    Importer = make_link("import_registry", _("Importer"))
    Groups = make_link("admin:auth_group_changelist", _("Groups"))
    NextOfKinRelationship = make_link(
        "admin:patients_nextofkinrelationship_changelist",
        _("Next of Kin Relationship"),
    )
    AddressTypes = make_link(
        "admin:patients_addresstype_changelist", _("Address Types")
    )
    States = make_link("admin:patients_state_changelist", _("States"))
    ClinicianOther = make_link(
        "admin:patients_clinicianother_changelist", _("Other Clinicians")
    )
    EmailNotification = make_link(
        "admin:rdrf_emailnotification_changelist", _("Email Notifications")
    )
    EmailTemplate = make_link(
        "admin:rdrf_emailtemplate_changelist", _("Email Templates")
    )
    EmailNotificationHistory = make_link(
        "admin:rdrf_emailnotificationhistory_changelist",
        _("Email Notifications History"),
    )
    RegistrationProfiles = make_link(
        "admin:registration_registrationprofile_changelist",
        _("Registration Profiles"),
    )
    LoginLog = make_link(
        "admin:useraudit_loginlog_changelist", _("User Login Log")
    )
    FailedLoginLog = make_link(
        "admin:useraudit_failedloginlog_changelist", _("User Failed Login Log")
    )
    LoginAttempts = make_link(
        "admin:useraudit_loginattempt_changelist", _("User Login Attempts Log")
    )
    Sites = make_link("admin:sites_site_changelist", _("Sites"))
    ParentGuardian = make_link(
        "admin:patients_parentguardian_changelist", _("Parents/Guardians")
    )

    DemographicsFields = make_link(
        "admin:rdrf_demographicfields_changelist",
        _("Registry Demographics Fields"),
    )
    ConsentRules = make_link(
        "admin:rdrf_consentrule_changelist", _("Consent Rules")
    )

    RegistryForms = make_link(
        "admin:rdrf_registryform_changelist", _("Registry Forms")
    )
    Sections = make_link(
        "admin:rdrf_section_changelist", _("Registry Sections")
    )
    DataElements = make_link(
        "admin:rdrf_commondataelement_changelist",
        _("Registry Common Data Elements"),
    )
    PermissibleValueGroups = make_link(
        "admin:rdrf_cdepermittedvaluegroup_changelist",
        _("Registry Permissible Value Groups"),
    )
    PermissibleValues = make_link(
        "admin:rdrf_cdepermittedvalue_changelist",
        _("Registry Permissible Values"),
    )
    ConsentSections = make_link(
        "admin:rdrf_consentsection_changelist", _("Registry Consent Sections")
    )
    ConsentValues = make_link(
        "admin:patients_consentvalue_changelist", _("Registry Consent Values")
    )
    CdePolicy = make_link(
        "admin:rdrf_cdepolicy_changelist",
        _("Registry Common Data Elements Policy"),
    )
    ContextFormGroups = make_link(
        "admin:rdrf_contextformgroup_changelist",
        _("Registry Context Form Groups"),
    )
    ConsentConfig = make_link(
        "admin:rdrf_consentconfiguration_changelist",
        _("Registry Consent Configuration"),
    )
    FormTitlesConfig = make_link(
        "admin:rdrf_formtitle_changelist", _("Registry Form Titles")
    )
    Dashboards = make_link(
        "admin:rdrf_registrydashboard_changelist", _("Dashboards")
    )
    DashboardWidgets = make_link(
        "admin:rdrf_registrydashboardwidget_changelist", _("Dashboard Widgets")
    )
    LongitudinalFollowups = make_link(
        "admin:rdrf_longitudinalfollowup_changelist",
        _("Longitudinal Followups"),
    )
    LongitudinalFollowupEntries = make_link(
        "admin:patients_longitudinalfollowupentry_changelist",
        _("Longitudinal Followup Entries"),
    )
    RegistryFormTranslation = make_link(
        "admin:rdrf_registryformtranslation_changelist",
        _("Registry Form Translations"),
    )
    WhitelistedFileExtension = make_link(
        "admin:rdrf_whitelistedfileextension_changelist",
        _("Allowed extensions for file uploads"),
    )
    TotpDevices = make_link(
        "admin:otp_totp_totpdevice_changelist", _("Totp Devices")
    )


class Links:
    """
    All links that can appear in menus are defined.
    Links are also grouped into related functional areas to make for easier assignment to menus
    """

    # related links are grouped or convenience
    REGISTRY_DESIGN = make_entries(
        LinkDefs.Registries,
        LinkDefs.RegistryForms,
        LinkDefs.Sections,
        LinkDefs.DataElements,
        LinkDefs.CdePolicy,
        LinkDefs.PermissibleValueGroups,
        LinkDefs.PermissibleValues,
        LinkDefs.ConsentConfig,
        LinkDefs.ConsentSections,
        LinkDefs.ConsentValues,
        LinkDefs.ContextFormGroups,
        LinkDefs.Dashboards,
        LinkDefs.DashboardWidgets,
    )

    # When enabled, doctors links
    ENABLED_DOCTORS = make_entries(LinkDefs.Doctors)

    # When enabled, patient user links
    ENABLED_PATIENT_USER = make_entries(LinkDefs.PatientUser)

    # When enabled, registration links
    ENABLED_REGISTRATION = make_entries(
        LinkDefs.ParentGuardian,
        LinkDefs.RegistrationProfiles,
        LinkDefs.ClinicianOther,
    )

    # When enabled, longitudinal followup links
    ENABLED_LONGITUDINAL_FOLLOWUPS = make_entries(
        LinkDefs.LongitudinalFollowups,
        LinkDefs.LongitudinalFollowupEntries,
    )

    # When enabled, registry form translation links
    ENABLED_REGISTRY_TRANSLATION = make_entries(
        LinkDefs.RegistryFormTranslation,
    )

    # When enabled, patient stages links and patient stage rules
    ENABLED_STAGES = make_entries(
        LinkDefs.PatientStages, LinkDefs.PatientStageRules
    )

    # only appear if related registry specific feature is set
    # Populated at runtime
    PATIENTS = {}
    PARENT_PATIENTS = {}
    PATIENT_USER = {}
    CONSENT = {}
    DOCTORS = {}
    FAMILY_LINKAGE = {}
    PERMISSIONS = {}
    REGISTRATION = {}
    LONGITUDINAL_FOLLOWUPS = {}
    REGISTRY_TRANSLATION = {}
    STAGES = {}

    USER_MANAGEMENT = make_entries(LinkDefs.Users)


class RegularLinks(Links):
    AUDITING = make_entries(
        LinkDefs.LoginLog, LinkDefs.FailedLoginLog, LinkDefs.LoginAttempts
    )
    EMAIL = make_entries(
        LinkDefs.EmailNotification,
        LinkDefs.EmailTemplate,
        LinkDefs.EmailNotificationHistory,
    )
    OTHER = make_entries(
        LinkDefs.Sites,
        LinkDefs.Groups,
        LinkDefs.Importer,
        LinkDefs.DemographicsFields,
        LinkDefs.NextOfKinRelationship,
        LinkDefs.AddressTypes,
        LinkDefs.ArchivedPatients,
        LinkDefs.ConsentRules,
        LinkDefs.FormTitlesConfig,
        LinkDefs.WhitelistedFileExtension,
        LinkDefs.TotpDevices,
    )

    WORKING_GROUPS = make_entries(
        LinkDefs.WorkingGroups, LinkDefs.WorkingGroupTypes
    )
    STATE_MANAGEMENT = make_entries(LinkDefs.States)


class PermissionBasedLinks(Links):
    REPORTS = ("can_run_reports", ReportDesign, make_entries(LinkDefs.Reports))

    ALL = (REPORTS,)


class MenuConfig:
    """
    Class to store the menu configuration. Defined for namespace purposes
    """

    def __init__(self, registries):
        self.registries = registries
        self.patient = {}
        self.parent = {}
        self.working_group_staff = {}
        self.working_group_curator = {}
        self.clinical = {}
        self.super_user = {}
        self.settings = {}
        self.all = {}
        self.build_menu()

    def group_links(self, group_name):
        group = groups.reverse_lookup(group_name)
        if group is None:
            return {}
        attr_name = group.lower()
        return getattr(self, attr_name, {})

    def permission_links(self, group_name):
        def has_permission(group, codename, model):
            return (
                group
                and group.permissions.filter(
                    codename=codename,
                    content_type=ContentType.objects.get_for_model(model),
                ).exists()
            )

        is_super_user = group_name == RDRF_GROUPS.SUPER_USER
        group_model = Group.objects.filter(name__iexact=group_name).first()

        return {
            key: val
            for codename, model, link_entries in PermissionBasedLinks.ALL
            for key, val in link_entries.items()
            if is_super_user or has_permission(group_model, codename, model)
        }

    def per_registry_links(self, label, url, feature=None):
        # build any per registry links that require the registry code as a param
        rval = {}
        for registry in self.registries:
            # don't provide per registry links to a registy that doesn't support feature
            if feature and not registry.has_feature(feature):
                continue

            try:
                text = label + " (" + registry.name + ")"
                qlink = QuickLink(
                    reverse_lazy(url, args=(registry.code,)), _(text)
                )
                rval[text] = qlink
            except NoReverseMatch:
                logging.exception(
                    "No reverse url for {0} with registry code {1}".format(
                        url, registry.code
                    )
                )
        return rval

    def patient_user_links(self):
        if any(
            r.has_feature(RegistryFeatures.PATIENTS_CREATE_USERS)
            for r in self.registries
        ):
            Links.PATIENT_USER = Links.ENABLED_PATIENT_USER

    def registration_links(self):
        if any(registry.registration_allowed() for registry in self.registries):
            Links.REGISTRATION = Links.ENABLED_REGISTRATION

    def longitudinal_followup_links(self):
        if any(
            registry.has_feature(RegistryFeatures.LONGITUDINAL_FOLLOWUPS)
            for registry in self.registries
        ):
            Links.LONGITUDINAL_FOLLOWUPS = Links.ENABLED_LONGITUDINAL_FOLLOWUPS

    def registry_translation_links(self):
        if any(
            registry.has_feature(RegistryFeatures.FORMS_REQUIRE_TRANSLATION)
            for registry in self.registries
        ):
            Links.REGISTRY_TRANSLATION = Links.ENABLED_REGISTRY_TRANSLATION

    def doctors_link(self):
        if any(
            registry.has_feature(RegistryFeatures.DOCTORS_LIST)
            for registry in self.registries
        ):
            Links.DOCTORS = Links.ENABLED_DOCTORS

    def family_linkage_links(self):
        Links.FAMILY_LINKAGE = self.per_registry_links(
            "Family Linkage", "family_linkage", RegistryFeatures.FAMILY_LINKAGE
        )

        # special case: if we have family linkage enabled, we enable doctors links
        if len(Links.FAMILY_LINKAGE) > 0:
            Links.DOCTORS = Links.ENABLED_DOCTORS

    def patient_stages_links(self):
        has_stages = any(
            registry.has_feature(RegistryFeatures.STAGES)
            for registry in self.registries
        )
        if has_stages and settings.DESIGN_MODE:
            Links.STAGES = Links.ENABLED_STAGES

    def patient_links(self):
        return {}

    def parent_patient_links(self):
        return {}

    def consent_links(self):
        return {}

    def permission_matrix_links(self):
        return {}

    def settings_links(self):
        raise NotImplementedError

    def menu_links(self, groups):
        raise NotImplementedError

    def admin_page_links(self):
        # get links for the admin page
        return self.all

    def build_menu(self):
        # enable dynamic links and build the menu
        self.patient_links()
        self.parent_patient_links()
        self.patient_user_links()
        self.consent_links()
        self.doctors_link()
        self.family_linkage_links()
        self.permission_matrix_links()
        self.registration_links()
        self.longitudinal_followup_links()
        self.registry_translation_links()
        self.patient_stages_links()


class RegularMenuConfig(MenuConfig):
    def __init__(self, registries):
        super().__init__(registries)
        self.working_group_staff = {**RegularLinks.PATIENTS}

        self.working_group_curator = {
            **RegularLinks.CONSENT,
            **RegularLinks.PATIENTS,
            **RegularLinks.DOCTORS,
            **RegularLinks.USER_MANAGEMENT,
        }

        self.clinical = {
            **RegularLinks.PATIENTS,
        }

        self.parent = {
            **RegularLinks.PARENT_PATIENTS,
        }

        # Super user has combined menu of all other users
        self.super_user = {
            **self.working_group_staff,
            **self.working_group_curator,
            **self.clinical,
        }

        # settings menu
        self.settings = {
            **RegularLinks.AUDITING,
            **RegularLinks.DOCTORS,
            **RegularLinks.FAMILY_LINKAGE,
            **RegularLinks.PERMISSIONS,
            **RegularLinks.REGISTRATION,
            **RegularLinks.LONGITUDINAL_FOLLOWUPS,
        }

        normal_menus = {
            **RegularLinks.AUDITING,
            **RegularLinks.CONSENT,
            **RegularLinks.PATIENTS,
            **RegularLinks.PATIENT_USER,
            **RegularLinks.DOCTORS,
            **RegularLinks.EMAIL,
            **RegularLinks.FAMILY_LINKAGE,
            **RegularLinks.OTHER,
            **RegularLinks.PERMISSIONS,
            **RegularLinks.REGISTRATION,
            **RegularLinks.LONGITUDINAL_FOLLOWUPS,
            **RegularLinks.STATE_MANAGEMENT,
            **RegularLinks.USER_MANAGEMENT,
            **RegularLinks.WORKING_GROUPS,
            **RegularLinks.STAGES,
            **RegularLinks.REGISTRY_TRANSLATION,
        }

        # menu with everything, used for the admin page
        self.all = normal_menus

        for codename, model, link_entries in PermissionBasedLinks.ALL:
            self.all.update(link_entries)

        if settings.DESIGN_MODE:
            self.all.update({**Links.REGISTRY_DESIGN})

    def patient_links(self):
        Links.PATIENTS = self.per_registry_links("Patient List", "patient_list")

    def parent_patient_links(self):
        Links.PARENT_PATIENTS = self.per_registry_links(
            "Patients", "registry:parent_page"
        )

    def consent_links(self):
        Links.CONSENT = self.per_registry_links("Consents", "consent_list")

    def permission_matrix_links(self):
        Links.PERMISSIONS = self.per_registry_links(
            "Permissions", "permission_matrix"
        )

    def settings_links(self):
        return self.settings

    def menu_links(self, groups):
        ret_val = {}
        group_links = reduce(add_dicts, map(self.group_links, groups), {})
        permission_links = reduce(
            add_dicts, map(self.permission_links, groups), {}
        )

        ret_val.update(group_links)
        ret_val.update(permission_links)

        return ret_val


class QuickLinks:
    """
    A convenience class to make it easy to see what links are provided to users on the "Home" screen
    """

    REGULAR_MENU_CONFIG = RegularMenuConfig

    def __init__(self, registries):
        self.menu_config = self.REGULAR_MENU_CONFIG(registries)

    def menu_links(self, groups):
        return ordered_links(self.menu_config.menu_links(groups))

    def settings_links(self):
        return ordered_links(self.menu_config.settings_links())

    def admin_page_links(self):
        return ordered_links(self.menu_config.admin_page_links())


def ordered_links(links):
    return sorted(links.values(), key=attrgetter("text"))


def add_dicts(d1, d2):
    return {**d1, **d2}

from django.urls import re_path, include, path
from django.contrib import admin
from django.views.generic.base import TemplateView
from django.contrib.auth import views as auth_views
from django.views.i18n import JavaScriptCatalog
from django.conf import settings
from django.utils.translation import gettext as _

from two_factor import views as twv

from rdrf.auth.forms import RDRFPasswordResetForm, RDRFSetPasswordForm
from rdrf.auth.views import LoginView, login_assistance_confirm, QRGeneratorView, SetupView, DisableView
from rdrf.forms.password_change import PasswordChangeForm

from rdrf.views import favicon_view, dashboard_view
import rdrf.views.form_view as form_view
import rdrf.views.registry_view as registry_view
import rdrf.views.landing_view as landing_view
import rdrf.views.import_registry_view as import_registry_view
import rdrf.views.patient_view as patient_view
import rdrf.routing.login_router as login_router
import rdrf.views.report_view as report_view
import rdrf.views.consent_view as consent_view
from rdrf.views.email_preferences_view import EmailPreferencesView, UnsubscribeAllView
from rdrf.views.handler_views import handler404, handler500, handler_application_error, handler_exceptions
from rdrf.views.health_check import health_check
from rdrf.views.mailbox_view import MailboxView, MailboxEmptyView
from rdrf.views.registration_rdrf import EmbeddedRegistrationCompletedView, EmbeddedRegistrationView, RdrfRegistrationView, PatientActivationView
from rdrf.views.lookup_views import PatientLookup
from rdrf.views.family_linkage import FamilyLinkageView
from rdrf.views.email_notification_view import ResendEmail
from rdrf.views.permission_matrix import PermissionMatrixView
from rdrf.views.context_views import RDRFContextCreateView, RDRFContextEditView
from rdrf.views import patients_listing
from rdrf.views import clinician_view
from rdrf.views.copyright_view import CopyrightView
from rdrf.views.session_refresh_view import session_refresh

from rdrf.views.actions import ActionExecutorView
import logging

from report.TrrfGraphQLView import TrrfGraphQLView
from report.schema import create_dynamic_schema

logger = logging.getLogger(__name__)

# very important so that registry admins (patient, etc) are discovered.
admin.autodiscover()

JavaScriptCatalog.domain = "django"  # The default domain didn't work for me

patterns = [
    path('favicon.ico', favicon_view.redirect_to_static, name='favicon'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type="text/plain"), name='robots_txt'),
]

if settings.DEBUG is True:
    patterns += [
        re_path(r'^test404', handler404, name='test 404'),
        re_path(r'^test500', handler500, name='test 500'),
        re_path(r'^testAppError', handler_application_error, name='test application error'),
        re_path(r'^raise', handler_exceptions, name='test exception'),
        re_path(r'mail/outbox/empty', MailboxEmptyView.as_view(), name='mailbox_empty'),
        re_path(r'mail/outbox', MailboxView.as_view(), name='mailbox'),
        path('graphql', lambda request: TrrfGraphQLView.as_view(schema=create_dynamic_schema(), graphiql=True)(request))
    ]


two_factor_auth_urls = [
    re_path(r'^account/login/?$', LoginView.as_view(), name='login'),
    re_path(r'^account/two_factor/setup/?$', SetupView.as_view(), name='setup'),
    re_path(r'^account/two_factor/qrcode/?$', QRGeneratorView.as_view(), name='qr'),
    re_path(r'^account/two_factor/setup/complete/?$', twv.SetupCompleteView.as_view(),
            name='setup_complete'),
    re_path(r'^account/two_factor/disable/?$', DisableView.as_view(), name='disable'),
]

patterns += [
    re_path(r'^silk/', include('silk.urls', namespace='silk')) if settings.PROFILING else None,
    re_path(r'^actions/?$', ActionExecutorView.as_view(), name='action'),
    re_path(r'^translations/jsi18n/$', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    re_path(r'^useraudit/', include('useraudit.urls',)),

    re_path(r'^api/v1/', include(('rdrf.services.rest.urls.api_urls', 'api_urls'), namespace='v1')),
    re_path(r'^rpc', form_view.RPCHandler.as_view(), name='rpc'),

    re_path(r'^admin/cde/(?P<code>\w+)/(?P<new_name>[\s\S]+)/settings/?$', form_view.CdeWidgetSettingsView.as_view(), name='cde_widget_settings'),
    re_path(r'^admin/cde/widgets/(?P<data_type>\w+)/?$', form_view.CdeAvailableWidgetsView.as_view(), name='cde_available_widgets'),
    path('admin/', admin.site.urls),


    re_path(r'', include((two_factor_auth_urls, 'two_factor'), namespace=None)),

    # django.contrib.auth URLs listed explicitly so we can override some of them for custom behaviour
    # Kept the original urls commented out to have an easy view on which URLs are customised.
    # Login is done by two_factor:login included above

    re_path(r'^logout/?$', auth_views.LogoutView.as_view(), name='logout'),
    re_path(r'^password_change/?$', auth_views.PasswordChangeView.as_view(form_class=PasswordChangeForm), name='password_change'),
    re_path(r'^password_change/done/?$', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    re_path(r'^password_reset/?$', auth_views.PasswordResetView.as_view(),
            kwargs={'password_reset_form': RDRFPasswordResetForm}, name='password_reset'),
    re_path(r'^password_reset/done/?$', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    re_path(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]+-[0-9A-Za-z]+)/?$',
            auth_views.PasswordResetConfirmView.as_view(form_class=RDRFSetPasswordForm),
            name='password_reset_confirm'),
    re_path(r'^reset/done/?$', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Login trouble self assistance URLs
    re_path(r'^login_assistance/?$', auth_views.PasswordResetView.as_view(form_class=RDRFPasswordResetForm),
            name='login_assistance'),
    re_path(r'^login_assistance/sent/?$', auth_views.PasswordResetDoneView.as_view(),
            kwargs={'template_name': 'registration/login_assistance_sent.html',
                    'extra_context': {'title': _('Login Assistance Email Sent')}},
            name='login_assistance_email_sent'),
    re_path(r'^login_assistance_confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]+-[0-9A-Za-z]+)/?$',
            login_assistance_confirm,
            name='login_assistance_confirm'),
    re_path(r'^login_assistance/complete/?$', auth_views.PasswordResetCompleteView.as_view(),
            kwargs={'template_name': 'registration/login_assistance_complete.html'},
            name='login_assistance_complete'),

    # --- Unsubscribe public views
    re_path(r'^unsubscribe_all/(?P<username_b64>\w+)/(?P<token>[\w.:\-_=]+)/?$', UnsubscribeAllView.as_view(),
            name='unsubscribe_all'),
    re_path(r'^unsubscribe_preferences/(?P<username_b64>\w+)/(?P<token>[\w.:\-_=]+)/?$', EmailPreferencesView.as_view(), name='email_preferences'),
    re_path(r'^email_preferences/?$', EmailPreferencesView.as_view(), name='email_preferences'),
    # ---

    # ------ Copyright URL -----------
    re_path(r"^copyright/?$", CopyrightView.as_view(), name="copyright"),

    re_path(r'', include(('registry.urls', 'registry_urls'), namespace="registry")),

    re_path(r'^$', landing_view.LandingView.as_view(), name='landing'),
    re_path(r'^import/?$', import_registry_view.ImportRegistryView.as_view(),
            name='import_registry'),
    re_path(r'^reports/?$', report_view.ReportView.as_view(), name="reports"),
    re_path(r'^reportdatatable/(?P<query_model_id>\d+)/?$', report_view.ReportDataTableView.as_view(),
            name="report_datatable"),
    re_path(r'^explorer/', include(('explorer.urls', 'explorer_urls'), namespace=None)),
    re_path(r'^report/', include(('report.urls', 'report_urls'), namespace='report')),
    re_path(r'^patientslisting/?$', patients_listing.PatientsListsView.as_view(), name="patientslisting"),
    re_path(r'^dashboards/?$', dashboard_view.DashboardListView.as_view(), name='parent_dashboard_list'),
    re_path(r'^contexts/(?P<registry_code>\w+)/(?P<patient_id>\d+)/add/(?P<context_form_group_id>\d+)?$',
            RDRFContextCreateView.as_view(),
            name="context_add"),
    re_path(r'contexts/(?P<registry_code>\w+)/(?P<patient_id>\d+)/(?P<context_id>\d+)/edit/?$',
            RDRFContextEditView.as_view(),
            name="context_edit"),
    re_path(r'^router/', login_router.RouterView.as_view(), name="login_router"),

    re_path(r"^cde_query/(?P<registry_code>\w+)/(?P<patient_id>\d+)/(?P<cde_code>\w+)?$",
            form_view.CdeCalculatedQueryLookup.as_view(), name='cde_query'),

    re_path(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<context_id>add)/?$",
            form_view.FormView.as_view(), name='form_add'),

    re_path(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<context_id>\d+)?$",
            form_view.FormView.as_view(), name='registry_form'),

    re_path(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/list/?$",
            form_view.FormListView.as_view(), name='registry_form_list'),

    re_path(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<section_code>\w+)/(?P<context_id>\d+)?/(?P<cde_code>\w+)/history/?$",
            form_view.FormFieldHistoryView.as_view(), name='registry_form_field_history'),

    re_path(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<section_code>\w+)/(?P<context_id>\d+)?/(?P<cde_code>\w+)/(?P<formset_index>\d+)?/history/?$",
            form_view.FormFieldHistoryView.as_view(), name='registry_form_field_history'),

    re_path(r"^forms/dsl-help$",
            form_view.FormDSLHelpView.as_view(), name='registry_form_dsl_help'),

    re_path(r"^(?P<registry_code>\w+)/?$",
            registry_view.RegistryView.as_view(), name='registry'),

    re_path(r'^(?P<registry_code>\w+)/dashboard/?$', dashboard_view.ParentDashboardView.as_view(), name='parent_dashboard'),

    re_path(r'^(?P<registry_code>\w+)/patientslisting/?$',
            patients_listing.PatientsListingView.as_view(), name="patient_list"),

    re_path(r"^(?P<registry_code>\w+)/patient/add/?$",
            patient_view.AddPatientView.as_view(), name='patient_add'),

    re_path(r"^(?P<registry_code>\w+)/patient/(?P<patient_id>\d+)/edit$",
            patient_view.PatientEditView.as_view(), name='patient_edit'),

    re_path(r"^(?P<registry_code>\w+)/permissions/?$",
            PermissionMatrixView.as_view(), name='permission_matrix'),

    # ---- Consent related URLs -----------------
    re_path(r"^(?P<registry_code>\w+)/consent/?$",
            consent_view.ConsentList.as_view(), name='consent_list'),

    re_path(r"^(?P<registry_code>\w+)/consent/(?P<section_id>\d+)/(?P<patient_id>\d+)/?$",
            consent_view.ConsentDetails.as_view(), name='consent_details'),

    re_path(r"^(?P<registry_code>\w+)/consent/print/?$",
            consent_view.PrintConsentList.as_view(), name='print_consent_list'),

    re_path(r"^(?P<registry_code>\w+)/(?P<patient_id>\d+)/consents/?$",
            form_view.CustomConsentFormView.as_view(), name="consent_form_view"),


    # ---- Clinician related URLs -----------------
    re_path(r"^(?P<registry_code>\w+)/(?P<patient_id>\d+)/clinician/?$",
            clinician_view.ClinicianFormView.as_view(), name="clinician_form_view"),

    re_path(r'^clinicianactivate/(?P<activation_key>\w+)/?$',
            clinician_view.ClinicianActivationView.as_view(),
            name='clinician_activate'),

    # ---- Email Notifications URLs -------------
    re_path(r"^resend_email/(?P<notification_history_id>\w+)/?$",
            ResendEmail.as_view(), name="resend_email"),
    # -------------------------------------------
    re_path(r"^(?P<registry_code>\w+)/familylinkage/(?P<initial_index>\d+)?$",
            FamilyLinkageView.as_view(), name='family_linkage'),

    re_path(r'^(?P<registry_code>\w+)/questionnaire/(?P<questionnaire_context>\w+)?$',
            form_view.QuestionnaireView.as_view(), name='questionnaire'),
    re_path(r'^(?P<registry_code>\w+)/approval/(?P<questionnaire_response_id>\d+)/?$', form_view.QuestionnaireHandlingView.as_view(),
            name='questionnaire_response'),
    re_path(r'^(?P<registry_code>\w+)/uploads/(?P<file_id>([0-9a-fA-F]{24})|(\d+))$',
            form_view.FileUploadView.as_view(), name='file_upload'),
    re_path(r'^questionnaireconfig/(?P<form_pk>\d+)/?$',
            form_view.QuestionnaireConfigurationView.as_view(), name='questionnaire_config'),

    # Disabled as no registries use Family Linkage currently. Make sure it is secure if it needs to be re-enabled!
    # re_path(r'api/familylookup/(?P<reg_code>\w+)/?$', FamilyLookup.as_view(), name="family_lookup"),

    re_path(r'api/patientlookup/(?P<reg_code>\w+)/?$', PatientLookup.as_view(), name="patient_lookup"),

    # --- Embeddable registration views
    re_path(r'^(?P<registry_code>\w+)/embed/register/complete/?$',
            EmbeddedRegistrationCompletedView.as_view(
                template_name='registration/registration_complete_simple.html'),
            name='embedded_registration_complete'),
    re_path(r'^(?P<registry_code>\w+)/embed/register/?$',
            EmbeddedRegistrationView.as_view(),
            name='embedded_registration_register'),
    # ---

    re_path(r'^(?P<registry_code>\w+)/register/?$',
            RdrfRegistrationView.as_view(),
            name='registration_register'),
    re_path(r'^register/complete/?$',
            TemplateView.as_view(
                template_name='registration/registration_complete.html'),
            name='registration_complete'),
    re_path(r'^register/failed/?$',
            TemplateView.as_view(
                template_name='registration/registration_failed.html'),
            name='registration_failed'),
    re_path(r'^register/closed/?$',
            TemplateView.as_view(
                template_name='registration/registration_closed.html'),
            name='registration_disallowed'),
    re_path(r'^activate/complete/?$',
            TemplateView.as_view(
                template_name='registration/activation_complete.html'),
            name='registration_activation_complete'),

    re_path(r'^activate/(?P<activation_key>\w+)/?$',
            PatientActivationView.as_view(),
            name='registration_activate'),

    re_path(r'^i18n/', include(('django.conf.urls.i18n', 'django_conf_urls'), namespace=None)),

    re_path(r'^health-check/?$', health_check, name='health_check'),
    re_path(r'^session-refresh/?$', session_refresh, name='session_refresh'),

]

urlpatterns = [u for u in patterns if u is not None]

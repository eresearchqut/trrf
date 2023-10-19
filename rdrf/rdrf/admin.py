import logging
from functools import partial
import datetime
import re

from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.forms import ChoiceField, ModelForm
from django.http import HttpResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from reversion.admin import VersionAdmin

from rdrf.admin_forms import CommonDataElementAdminForm
from rdrf.admin_forms import ConsentConfigurationAdminForm, RegistryDashboardAdminForm, DashboardWidgetAdminForm
from rdrf.admin_forms import ContextFormGroupItemAdminForm
from rdrf.admin_forms import DemographicFieldsAdminForm
from rdrf.admin_forms import EmailTemplateAdminForm
from rdrf.admin_forms import FormTitleAdminForm
from rdrf.admin_forms import RegistryFormAdminForm
from rdrf.events.events import EventType
from rdrf.exporter_utils import export_forms, export_context_form_groups, export_registries, export_registry_dashboards
from rdrf.models.definition.models import WhitelistedFileExtension
from rdrf.models.definition.models import CDEFile
from rdrf.models.definition.models import CDEPermittedValue
from rdrf.models.definition.models import CDEPermittedValueGroup
from rdrf.models.definition.models import CdePolicy
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ConsentConfiguration
from rdrf.models.definition.models import ConsentQuestion
from rdrf.models.definition.models import ConsentRule
from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import ContextFormGroup
from rdrf.models.definition.models import ContextFormGroupItem
from rdrf.models.definition.models import DemographicFields
from rdrf.models.definition.models import EmailNotification
from rdrf.models.definition.models import EmailNotificationHistory
from rdrf.models.definition.models import EmailTemplate
from rdrf.models.definition.models import FormTitle
from rdrf.models.definition.models import Notification
from rdrf.models.definition.models import Registry, RegistryDashboard, RegistryDashboardWidget, \
    RegistryDashboardFormLink, \
    RegistryDashboardCDEData, RegistryDashboardDemographicData, LongitudinalFollowup
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from report.utils import load_report_configuration
from registration.admin import RegistrationAdmin
from registration.models import RegistrationProfile

logger = logging.getLogger(__name__)


def export_wrapper(request, export_func):
    try:
        export_response = export_func()

        if isinstance(export_response, HttpResponse):
            return export_response
        else:
            # There were errors
            errors, item_str = export_response
            logger.error(f'Error(s) exporting {item_str}:')
            for error in errors:
                logger.error(f'Export Error: {error}')
                messages.error(request, f'Error in export of {item_str}: {error}')
                return None
    except Exception as ex:
        logger.exception(ex, exc_info=True)
        messages.error(request, "Custom Action Failed: %s" % ex)
        return None


@admin.action(description='Export')
def export_registry_action(modeladmin, request, registries):
    return export_wrapper(request, partial(export_registries, registries))


@admin.action(description='Export')
def export_context_form_group_action(modeladmin, request, context_form_groups):
    return export_wrapper(request, partial(export_context_form_groups, context_form_groups))


@admin.action(description='Export')
def export_registry_form_action(modeladmin, request, forms):
    return export_wrapper(request, partial(export_forms, forms))


@admin.action(description='Export')
def export_registry_dashboard_action(modeladmin, request, dashboards):
    return export_wrapper(request, partial(export_registry_dashboards, dashboards))


@admin.register(ClinicalData)
class BaseReversionAdmin(VersionAdmin):
    pass


class SectionAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name')
    ordering = ['code']
    search_fields = ['code', 'display_name']

    def has_add_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False


class RegistryFormAdmin(admin.ModelAdmin):
    list_display = ('registry', 'name', 'position')
    list_display_links = ('name',)
    ordering = ['registry', 'name']
    form = RegistryFormAdminForm
    search_fields = ['name']
    actions = [export_registry_form_action]

    list_filter = ['registry']

    def has_add_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False


class RegistryAdmin(admin.ModelAdmin):
    actions = [export_registry_action]

    def get_queryset(self, request):
        if not request.user.is_superuser:
            user = get_user_model().objects.get(username=request.user)
            return Registry.objects.filter(registry__in=[reg.id for reg in user.registry.all()])

        return Registry.objects.all()

    def has_add_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def get_urls(self):
        original_urls = super(RegistryAdmin, self).get_urls()

        return original_urls

    def get_readonly_fields(self, request, obj=None):
        "Registry code is readonly after creation"
        return () if obj is None else ("code",)


class ActivationKeyExpirationListFilter(admin.SimpleListFilter):
    title = _('activation key expired')
    parameter_name = 'activation_key_expired'

    def lookups(self, request, model_admin):
        return [
            ('True', _('Yes')),
            ('False', _('No')),
        ]

    def queryset(self, request, queryset):
        expired_profiles = [profile.id for profile in queryset if profile.activation_key_expired()]

        if self.value() == 'True':
            return queryset.filter(id__in=expired_profiles)
        elif self.value() == 'False':
            return queryset.exclude(id__in=expired_profiles)
        else:
            return queryset


def resend_activation_mail(profile, site, request=None):
    if not hasattr(profile.user, 'registrationprofile') or profile.activated:
        return False

    profile.create_new_activation_key()
    profile.send_activation_email(site, request)

    return True


class CustomRegistrationProfileAdmin(RegistrationAdmin):
    list_display = ('user', 'custom_activation_key_expired', 'activated')
    list_filter = ['activated', ActivationKeyExpirationListFilter]

    @admin.display(description="Activation key expired")
    def custom_activation_key_expired(self, obj):
        max_expiry_days = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        activation_date = obj.user.date_activated
        expiration_date = (obj.user.date_joined if activation_date is None else activation_date) + max_expiry_days

        return obj.activated or expiration_date <= datetime.datetime.now()

    def activate_user(self, activation_key):
        sha256_re = re.compile('^[a-f0-9]{40,64}$')

        def activate(user_profile):
            user = user_profile.user
            user.is_active = True
            user_profile.activated = True

            with transaction.atomic():
                user.save()
                user_profile.save()

            return user

        if sha256_re.search(activation_key):
            profile = RegistrationProfile.objects.filter(activation_key=activation_key)
            if not profile.exists():
                return False, False

            profile = profile.first()
            if not self.custom_activation_key_expired(profile):
                return activate(profile), True

        return False, False

    def activate_users(self, request, queryset):
        for profile in queryset:
            self.activate_user(profile.activation_key)

    def resend_activation_email(self, request, queryset):
        site = get_current_site(request)
        for profile in queryset:
            resend_activation_mail(profile, site, request)
            user = profile.user
            user.date_activated = datetime.datetime.now()
            user.save()


def create_restricted_model_admin_class(
        model_class,
        search_fields=None,
        ordering=None,
        list_display=None,
        form=None):

    def query_set_func(model_class):
        def queryset(myself, request):
            if not request.user.is_superuser:
                return []
            else:
                return model_class.objects.all()

        return queryset

    def make_perm_func():
        def perm(self, request, *args, **kwargs):
            return request.user.is_superuser
        return perm

    overrides = {
        "has_add_permission": make_perm_func(),
        "has_change_permission": make_perm_func(),
        "has_delete_permission": make_perm_func(),
        "queryset": query_set_func(model_class),
    }

    if search_fields:
        overrides["search_fields"] = search_fields
    if ordering:
        overrides["ordering"] = ordering
    if list_display:
        overrides["list_display"] = list_display
    if form:
        overrides["form"] = form
        overrides["change_form_template"] = form.template

    return type(model_class.__name__ + "Admin", (admin.ModelAdmin,), overrides)


class CDEPermittedValueAdmin(admin.StackedInline):
    model = CDEPermittedValue
    extra = 0

    fieldsets = (
        (None, {'fields': ('code', 'value', 'desc', 'position')}),
    )


class CDEPermittedValueGroupAdmin(admin.ModelAdmin):
    inlines = [CDEPermittedValueAdmin]


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created', 'from_username', 'to_username', 'message')


class ConsentQuestionAdmin(admin.StackedInline):
    model = ConsentQuestion
    extra = 0
    readonly_fields = ['created_at', 'last_updated_at']
    fieldsets = (
        (None, {
            'fields': (
                'position', 'code', 'question_label', 'instructions', 'created_at', 'last_updated_at')}), )


class ConsentSectionAdmin(admin.ModelAdmin):
    readonly_fields = ['created_at', 'last_updated_at', 'latest_change']
    list_display = ('registry', 'section_label')
    list_display_links = ('section_label',)
    inlines = [ConsentQuestionAdmin]

    def latest_change(self, obj):
        return obj.latest_update
    latest_change.short_description = 'Latest change (including questions)'


class ConsentConfigurationAdmin(admin.ModelAdmin):
    models = ConsentConfiguration
    form = ConsentConfigurationAdminForm
    list_display = ("registry", "esignature", "consent_locked")


class DemographicFieldsAdmin(admin.ModelAdmin):
    model = DemographicFields
    form = DemographicFieldsAdminForm
    list_display = ("registry", "field", "status")
    list_display_links = ("field",)


class CdePolicyAdmin(admin.ModelAdmin):
    model = CdePolicy
    list_display = ("registry", "cde", "groups", "condition")
    list_display_links = ("cde", )

    def groups(self, obj):
        return ", ".join([gr.name for gr in obj.groups_allowed.all()])

    groups.short_description = _("Allowed Groups")


class EmailNotificationAdmin(admin.ModelAdmin):
    model = EmailNotification
    list_display = ("description", "registry", "email_from", "recipient", "group_recipient")
    readonly_fields = ("warnings", )
    UPDATE_ONLY_FIELDS = ("file_uploaded_cdes", "warnings")

    def no_warnings(self, obj):
        return obj is None or obj.warnings is None
    no_warnings.boolean = True
    # Changing the display name to the opposite, as users would expect "red-cross" if there are warnings
    # and green check if there are none
    no_warnings.short_description = "Warnings"

    def any_warnings(self,):
        for obj in EmailNotification.objects.all():
            if not self.no_warnings(obj):
                return True
        return False

    def get_changeform_initial_data(self, request):
        return {'email_from': settings.DEFAULT_FROM_EMAIL}

    def get_list_display(self, request):
        list_display = super().get_list_display(request)

        if self.any_warnings():
            with_warnings_col = (list_display[0], "no_warnings") + list_display[1:]
            return with_warnings_col
        return list_display

    def get_fields(self, request, obj=None):
        all_fields = super().get_fields(request, obj)
        to_remove = set()
        # Always remove to change it's position
        to_remove.add("warnings")
        if obj is None:
            to_remove.update(self.UPDATE_ONLY_FIELDS)
        else:
            if obj.description != EventType.FILE_UPLOADED:
                to_remove.add("file_uploaded_cdes")
        fields = [f for f in all_fields if f not in to_remove]
        if not self.no_warnings(obj):
            fields.insert(2, 'warnings')
        return fields


class EmailTemplateAdmin(admin.ModelAdmin):
    model = EmailTemplate
    form = EmailTemplateAdminForm
    list_display = ("language", "description")
    list_display_links = ("description",)


class EmailNotificationHistoryAdmin(admin.ModelAdmin):
    model = EmailNotificationHistory
    list_display = ("date_stamp", "email_notification", "registry", "full_language", "resend")

    def registry(self, obj):
        return "%s (%s)" % (obj.email_notification.registry.name,
                            obj.email_notification.registry.code.upper())

    def full_language(self, obj):
        return dict(settings.LANGUAGES).get(obj.language, obj.language)

    full_language.short_description = "Language"

    def resend(self, obj):
        email_url = reverse('resend_email', args=(obj.id,))
        return mark_safe(f"<a class='btn btn-info btn-xs' href='{email_url}'>Resend</a>")
    resend.allow_tags = True


class ConsentRuleAdmin(admin.ModelAdmin):
    model = ConsentRule
    list_display = ("registry", "user_group", "capability", "consent_question", "enabled")
    list_display_links = ("user_group",)


class ContextFormGroupItemAdmin(admin.StackedInline):
    model = ContextFormGroupItem
    form = ContextFormGroupItemAdminForm


class ContextFormGroupAdmin(admin.ModelAdmin):
    model = ContextFormGroup
    list_display = ('name', 'registry')
    inlines = [ContextFormGroupItemAdmin]
    actions = [export_context_form_group_action]

    def registry(self, obj):
        return obj.registry.name

    class Media:
        js = ("js/admin/context_form_group_on_load.js", "js/admin/context_form_group_admin_change.js")


class CDEFileAdmin(admin.ModelAdmin):
    model = CDEFile
    list_display = ("form_name", "section_code", "cde_code", "item")


class FormTitleAdmin(admin.ModelAdmin):
    model = FormTitle
    form = FormTitleAdminForm
    list_display = ('registry', 'default_title', 'group_names', 'custom_title', 'order')
    list_display_links = ('default_title',)


class WhitelistedFileExtensionAdmin(admin.ModelAdmin):
    model = WhitelistedFileExtension
    list_display = ('file_extension',)
    ordering = ('file_extension',)


class DashboardLinksInline(admin.StackedInline):
    model = RegistryDashboardFormLink
    verbose_name_plural = 'Registry Form Links'
    autocomplete_fields = ('registry_form',)
    extra = 0


class DashboardCdeDataInline(admin.StackedInline):
    model = RegistryDashboardCDEData
    verbose_name_plural = 'Clinical Data'
    autocomplete_fields = ('registry_form', 'section', 'cde')
    extra = 0


class DashboardDemographicDataAdminForm(ModelForm):
    @staticmethod
    def get_patient_demographic_fields():
        demographic_model = load_report_configuration()['demographic_model']
        field_choices = [('', '---------')]
        field_choices.extend([(field, _(label)) for field, label in demographic_model['patient']['fields'].items()])
        return field_choices

    field = ChoiceField()

    class Meta:
        model = RegistryDashboardDemographicData
        exclude = []

    def __init__(self, *args, **kwargs):
        super(DashboardDemographicDataAdminForm, self).__init__(*args, **kwargs)
        self.fields['field'].choices = self.get_patient_demographic_fields()


class DashboardDemographicsInline(admin.StackedInline):
    form = DashboardDemographicDataAdminForm
    model = RegistryDashboardDemographicData
    verbose_name_plural = 'Patient Demographics'
    extra = 0


class RegistryDashboardAdmin(admin.ModelAdmin):
    model = RegistryDashboard
    form = RegistryDashboardAdminForm
    list_display = ('registry',)
    actions = [export_registry_dashboard_action]


class DashboardWidgetAdmin(admin.ModelAdmin):
    model = RegistryDashboardWidget
    form = DashboardWidgetAdminForm
    list_display = ('registry_dashboard', 'widget_type', 'title')
    list_display_links = ('widget_type',)
    list_select_related = ('registry_dashboard',)
    list_filter = ['registry_dashboard']
    inlines = [DashboardLinksInline, DashboardDemographicsInline, DashboardCdeDataInline]


class LongitudinalFollowupAdmin(admin.ModelAdmin):
    model = LongitudinalFollowup

    list_display = (
        "name",
        "context_form_group",
        "frequency",
        "debounce",
    )

    def get_changeform_initial_data(self, request):
        return {
            "frequency": datetime.timedelta(weeks=26),
            "debounce": datetime.timedelta(weeks=1),
        }


CDEPermittedValueAdmin = create_restricted_model_admin_class(
    CDEPermittedValue,
    ordering=['code'],
    search_fields=[
        'code',
        'value',
        'pv_group__code'],
    list_display=[
        'code',
        'value',
        'pvg_link',
        'position_formatted'])

CommonDataElementAdmin = create_restricted_model_admin_class(
    CommonDataElement,
    ordering=['code'],
    search_fields=[
        'code',
        'name',
        'datatype'],
    list_display=[
        'code',
        'name',
        'datatype',
        'widget_name'],
    form=CommonDataElementAdminForm)

DESIGN_MODE_ADMIN_COMPONENTS = [
    (Registry, RegistryAdmin),
    (CDEPermittedValue, CDEPermittedValueAdmin),
    (CommonDataElement, CommonDataElementAdmin),
    (CDEPermittedValueGroup, CDEPermittedValueGroupAdmin),
    (RegistryForm, RegistryFormAdmin),
    (ConsentConfiguration, ConsentConfigurationAdmin),
    (WhitelistedFileExtension, WhitelistedFileExtensionAdmin),
    (Section, SectionAdmin),
    (ConsentSection, ConsentSectionAdmin),
    (CdePolicy, CdePolicyAdmin),
    (ContextFormGroup, ContextFormGroupAdmin),
    (CDEFile, CDEFileAdmin),
    (RegistryDashboard, RegistryDashboardAdmin),
    (RegistryDashboardWidget, DashboardWidgetAdmin),
    (LongitudinalFollowup, LongitudinalFollowupAdmin),
]

NORMAL_MODE_ADMIN_COMPONENTS = [
    (Registry, RegistryAdmin),
    (EmailNotification, EmailNotificationAdmin),
    (EmailTemplate, EmailTemplateAdmin),
    (EmailNotificationHistory, EmailNotificationHistoryAdmin),
    (Notification, NotificationAdmin),
    (DemographicFields, DemographicFieldsAdmin),
    (ConsentRule, ConsentRuleAdmin),
    (FormTitle, FormTitleAdmin),
    (WhitelistedFileExtension, WhitelistedFileExtensionAdmin),
]

ADMIN_COMPONENTS = NORMAL_MODE_ADMIN_COMPONENTS

if settings.DESIGN_MODE:
    ADMIN_COMPONENTS += DESIGN_MODE_ADMIN_COMPONENTS

for model_class, model_admin in ADMIN_COMPONENTS:
    if not admin.site.is_registered(model_class):
        admin.site.register(model_class, model_admin)

admin.site.unregister(RegistrationProfile)
admin.site.register(RegistrationProfile, CustomRegistrationProfileAdmin)

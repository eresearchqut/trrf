from django.db import transaction, IntegrityError
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.contrib import admin
from django.urls import reverse

from rdrf.events.events import EventType
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import QuestionnaireResponse
from rdrf.models.definition.models import CDEPermittedValue
from rdrf.models.definition.models import Notification
from rdrf.models.definition.models import CDEPermittedValueGroup
from rdrf.models.definition.models import ConsentConfiguration
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import ConsentQuestion
from rdrf.models.definition.models import DemographicFields
from rdrf.models.definition.models import CdePolicy
from rdrf.models.definition.models import EmailNotification
from rdrf.models.definition.models import EmailTemplate
from rdrf.models.definition.models import EmailNotificationHistory
from rdrf.models.definition.models import ContextFormGroup
from rdrf.models.definition.models import ContextFormGroupItem
from rdrf.models.definition.models import CDEFile
from rdrf.models.definition.models import ConsentRule
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import FormTitle
from rdrf.models.proms.models import Survey
from rdrf.models.proms.models import SurveyQuestion
from rdrf.models.proms.models import Precondition
from rdrf.models.proms.models import SurveyAssignment
from rdrf.models.proms.models import SurveyRequest
from rdrf.system_role import SystemRoles


from reversion.admin import VersionAdmin

import logging
from django.http import HttpResponse
from wsgiref.util import FileWrapper
import io
from django.contrib import messages
from django.conf import settings

from django.contrib.auth import get_user_model

from rdrf.admin_forms import ConsentConfigurationAdminForm
from rdrf.admin_forms import RegistryFormAdminForm
from rdrf.admin_forms import EmailTemplateAdminForm
from rdrf.admin_forms import DemographicFieldsAdminForm
from rdrf.admin_forms import CommonDataElementAdminForm
from rdrf.admin_forms import ContextFormGroupItemAdminForm
from rdrf.admin_forms import FormTitleAdminForm

from functools import reduce

logger = logging.getLogger(__name__)


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
    list_display = ('registry', 'name', 'is_questionnaire', 'position')
    ordering = ['registry', 'name']
    form = RegistryFormAdminForm

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
    actions = ['export_registry_action', 'generate_questionnaire_action', 'enable_registration_action',
               'disable_registration_action', 'create_notifications_action']

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

    def get_readonly_fields(self, request, obj=None):
        "Registry code is readonly after creation"
        return () if obj is None else ("code",)

    @staticmethod
    def export_registry(registry, request):
        from rdrf.services.io.defs.exporter import Exporter
        exporter = Exporter(registry)
        logger.info("Exporting Registry %s" % registry.name)
        try:
            yaml_data, errors = exporter.export_yaml()
            if errors:
                logger.error("Error(s) exporting %s:" % registry.name)
                for error in errors:
                    logger.error("Export Error: %s" % error)
                    messages.error(request, "Error in export of %s: %s" %
                                   (registry.name, error))
                return None
            else:
                logger.info("Exported YAML Data for %s OK" % registry.name)
            return yaml_data
        except Exception as ex:
            logger.error("export registry action for %s error: %s" % (registry.name, ex))
            messages.error(request, "Custom Action Failed: %s" % ex)
            return None

    def export_registry_action(self, request, registry_models_selected):
        from datetime import datetime
        export_time = str(datetime.now())

        registries = list(registry_models_selected)

        if len(registries) == 1:
            registry = registries[0]
            yaml_export_filename = registry.name + ".yaml"
            yaml_data = self.export_registry(registry, request)
            if yaml_data is None:
                return

            yaml_file = io.StringIO()
            yaml_file.write(yaml_data)
            yaml_file.flush()
            yaml_file.seek(0)

            response = HttpResponse(FileWrapper(yaml_file), content_type='text/yaml')
            yaml_export_filename = "export_%s_%s" % (export_time, yaml_export_filename)
            response['Content-Disposition'] = 'attachment; filename="%s"' % yaml_export_filename

            return response
        else:
            import zipfile
            zipped_file = io.BytesIO()
            zf = zipfile.ZipFile(zipped_file, mode='w', compression=zipfile.ZIP_DEFLATED)

            for registry in registries:
                yaml_data = self.export_registry(registry, request)
                if yaml_data is None:
                    return

                zf.writestr(registry.code + '.yaml', yaml_data)

            zf.close()
            zipped_file.flush()
            zipped_file.seek(0)

            response = HttpResponse(FileWrapper(zipped_file), content_type='application/zip')
            name = "export_" + export_time + "_" + \
                   reduce(lambda x, y: x + '_and_' + y, [r.code for r in registries]) + ".zip"
            response['Content-Disposition'] = 'attachment; filename="%s"' % name

            return response
    export_registry_action.short_description = _("Export")

    def generate_questionnaire_action(self, request, registry_models_selected):
        for registry in registry_models_selected:
            registry.generate_questionnaire()

    generate_questionnaire_action.short_description = _("Generate Questionnaire")

    def enable_registration_action(self, request, registry_models_selected):
        unchanged = []

        for registry in registry_models_selected:
            if registry.has_feature(RegistryFeatures.REGISTRATION):
                unchanged.append(str(registry))
            else:
                registry.add_feature(RegistryFeatures.REGISTRATION)
                registry.save()

                messages.success(request, _(f"Registration enabled for {registry}"))

            existing_notifications = EmailNotification.objects.filter(
                registry=registry,
                description__in=EventType.REGISTRATION_TYPES,
            )

            if len(existing_notifications) > 0 and len(existing_notifications.filter(disabled=False)) == 0:
                messages.warning(request, render_to_string("admin/notifications_disabled.html", {
                    "registry": registry
                }))
            elif len(existing_notifications) == 0:
                messages.warning(request, render_to_string("admin/notifications_needed.html", {
                    "registry": registry
                }))

        if len(unchanged) > 0:
            messages.info(request, _(f"'{', '.join(desc for desc in unchanged)}' already enabled registration"))

    enable_registration_action.short_description = _("Enable registration")

    def disable_registration_action(self, request, registry_models_selected):
        unchanged = []

        for registry in registry_models_selected:
            if not registry.has_feature(RegistryFeatures.REGISTRATION):
                unchanged.append(str(registry))
            else:
                registry.remove_feature(RegistryFeatures.REGISTRATION)
                registry.save()

                messages.success(request, _(f"Registration disabled for {registry}"))

        if len(unchanged) > 0:
            messages.info(request, _(f"'{', '.join(desc for desc in unchanged)}' already had registration disabled"))

    disable_registration_action.short_description = _("Disable registration")

    def create_notifications_action(self, request, registry_models_selected):
        patient_registration_templates = EmailTemplate.objects.filter(
            default_for_notification=EventType.NEW_PATIENT
        )

        if not patient_registration_templates.exists():
            messages.error(request, _("Default email templates have not been created"))
            return

        for registry in registry_models_selected:
            # TODO: Add default notifications for all registration types. Needs different recipients.
            try:
                with transaction.atomic():
                    notification = EmailNotification(
                        description=EventType.NEW_PATIENT,
                        registry=registry,
                        recipient="{{ patient.user.email }}",
                    )
                    notification.save()

                    notification.email_templates.set(patient_registration_templates)
                    notification.save()

                    messages.success(request, render_to_string("admin/notifications_added.html", {
                        "registry": registry,
                    }))
            except IntegrityError as e:
                logger.error("Failed to create default registration notifications for %s: %s", registry, e)
                messages.error(request, _(f"Failed to create default registration notifications for {registry}"))

    create_notifications_action.short_description = _("Create default registration notifications")


class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ('registry', 'date_submitted', 'process_link', 'name', 'date_of_birth')
    list_filter = ('registry', 'date_submitted')

    def process_link(self, obj):
        if not obj.has_mongo_data:
            return "NO DATA"

        link = "-"
        if not obj.processed:
            url = reverse('questionnaire_response', args=(obj.registry.code, obj.id))
            link = "<a href='%s'>Review</a>" % url
        return link

    def get_queryset(self, request):
        user = request.user
        query_set = QuestionnaireResponse.objects.filter(processed=False)
        if user.is_superuser:
            return query_set
        else:
            return query_set.filter(
                registry__in=[
                    reg for reg in user.registry.all()],
            )

    process_link.allow_tags = True
    process_link.short_description = _('Process questionnaire')


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
        (None, {'fields': ('code', 'value', 'questionnaire_value', 'desc', 'position')}),
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
                'position', 'code', 'question_label', 'questionnaire_label', 'instructions', 'created_at', 'last_updated_at')}), )


class ConsentSectionAdmin(admin.ModelAdmin):
    readonly_fields = ['created_at', 'last_updated_at', 'latest_change']
    list_display = ('registry', 'section_label')
    inlines = [ConsentQuestionAdmin]

    def latest_change(self, obj):
        return obj.latest_update
    latest_change.short_description = 'Latest change (including questions)'


class ConsentConfigurationAdmin(admin.ModelAdmin):
    models = ConsentConfiguration
    forms = ConsentConfigurationAdminForm
    list_display = ("registry", "esignature", "consent_locked")


class DemographicFieldsAdmin(admin.ModelAdmin):
    model = DemographicFields
    form = DemographicFieldsAdminForm
    list_display = ("registry", "field", "status")


class CdePolicyAdmin(admin.ModelAdmin):
    model = CdePolicy
    list_display = ("registry", "cde", "groups", "condition")

    def groups(self, obj):
        return ", ".join([gr.name for gr in obj.groups_allowed.all()])

    groups.short_description = _("Allowed Groups")


class RegistryRegistrationNotificationFilter(admin.SimpleListFilter):
    title = _("Registry registration notifications")
    parameter_name = 'registry_registration'

    def lookups(self, request, model_admin):
        return [(reg.code, reg.name) for reg in Registry.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            registry = Registry.objects.get(code=self.value())
            return queryset.filter(registry=registry, description__in=EventType.REGISTRATION_TYPES)


class EmailNotificationAdmin(admin.ModelAdmin):
    model = EmailNotification
    list_display = ("description", "registry", "email_from", "recipient", "group_recipient", "disabled")
    list_filter = (RegistryRegistrationNotificationFilter, )

    def get_changeform_initial_data(self, request):
        from django.conf import settings
        return {'email_from': settings.DEFAULT_FROM_EMAIL}


class EmailTemplateAdmin(admin.ModelAdmin):
    model = EmailTemplate
    form = EmailTemplateAdminForm

    def __init__(self, model, admin_site):
        self.list_display = ("subject", "language", "description", self._default_and_lang)
        super().__init__(model, admin_site)

    def _default_and_lang(self, email_template):
        return f"{email_template.default_for_notification} ({email_template.language})" \
            if email_template.default_for_notification else "-"

    _default_and_lang.short_description = _("Default for notification")


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
        return "<a class='btn btn-info btn-xs' href='%s'>Resend</a>" % email_url
    resend.allow_tags = True


class ConsentRuleAdmin(admin.ModelAdmin):
    model = ConsentRule
    list_display = ("registry", "user_group", "capability", "consent_question", "enabled")


class PreconditionAdmin(admin.ModelAdmin):
    model = Precondition
    list_display = ('survey', 'cde', 'value')


class SurveyQuestionAdmin(admin.StackedInline):
    model = SurveyQuestion
    extra = 0
    list_display = ("registry", "name", "expression")
    inlines = [PreconditionAdmin]


class SurveyAdmin(admin.ModelAdmin):
    model = Survey
    list_display = ("registry", "name")
    inlines = [SurveyQuestionAdmin]


class SurveyRequestAdmin(admin.ModelAdmin):
    model = SurveyRequest
    list_display = ("patient_name", "survey_name", "patient_token", "created", "updated", "state", "error_detail", "user")
    search_fields = ("survey_name", "patient__family_name", "patient__given_names")
    list_display_links = None


class SurveyAssignmentAdmin(admin.ModelAdmin):
    model = SurveyAssignment
    list_display = ("registry", "survey_name", "patient_token", "state", "created", "updated", "response")


class ContextFormGroupItemAdmin(admin.StackedInline):
    model = ContextFormGroupItem
    form = ContextFormGroupItemAdminForm


class ContextFormGroupAdmin(admin.ModelAdmin):
    model = ContextFormGroup
    list_display = ('name', 'registry')
    inlines = [ContextFormGroupItemAdmin]

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
        'questionnaire_value_formatted',
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
    (Section, SectionAdmin),
    (ConsentSection, ConsentSectionAdmin),
    (CdePolicy, CdePolicyAdmin),
    (ContextFormGroup, ContextFormGroupAdmin),
    (CDEFile, CDEFileAdmin),
]

PROMS_ADMIN_COMPONENTS = [(Survey, SurveyAdmin),
                          (SurveyAssignment, SurveyAssignmentAdmin),
                          (SurveyRequest, SurveyRequestAdmin),
                          ]

NORMAL_MODE_ADMIN_COMPONENTS = [
    (Registry, RegistryAdmin),
    (QuestionnaireResponse, QuestionnaireResponseAdmin),
    (Precondition, PreconditionAdmin),
    (EmailNotification, EmailNotificationAdmin),
    (EmailTemplate, EmailTemplateAdmin),
    (EmailNotificationHistory, EmailNotificationHistoryAdmin),
    (Notification, NotificationAdmin),
    (DemographicFields, DemographicFieldsAdmin),
    (ConsentRule, ConsentRuleAdmin),
    (FormTitle, FormTitleAdmin)
]

ADMIN_COMPONENTS = []

if settings.SYSTEM_ROLE is SystemRoles.CIC_PROMS:
    ADMIN_COMPONENTS = PROMS_ADMIN_COMPONENTS

if settings.DESIGN_MODE:
    ADMIN_COMPONENTS = ADMIN_COMPONENTS + DESIGN_MODE_ADMIN_COMPONENTS

if settings.SYSTEM_ROLE in (SystemRoles.NORMAL, SystemRoles.NORMAL_NO_PROMS):
    ADMIN_COMPONENTS = ADMIN_COMPONENTS + NORMAL_MODE_ADMIN_COMPONENTS

if settings.SYSTEM_ROLE is SystemRoles.CIC_DEV:
    ADMIN_COMPONENTS = ADMIN_COMPONENTS + NORMAL_MODE_ADMIN_COMPONENTS + PROMS_ADMIN_COMPONENTS

if settings.SYSTEM_ROLE is SystemRoles.CIC_CLINICAL:
    ADMIN_COMPONENTS = ADMIN_COMPONENTS + NORMAL_MODE_ADMIN_COMPONENTS + PROMS_ADMIN_COMPONENTS

for model_class, model_admin in ADMIN_COMPONENTS:
    if not admin.site.is_registered(model_class):
        admin.site.register(model_class, model_admin)

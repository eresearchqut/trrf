from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.contrib import admin
from django.urls import reverse
from rdrf.events.events import EventType
from rdrf.models.definition.models import Registry, RegistryDashboard, RegistryDashboardWidget, \
    RegistryDashboardFormLink, \
    RegistryDashboardCDEData, RegistryDashboardDemographicData
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
from rdrf.models.definition.models import BlacklistedMimeType


from reversion.admin import VersionAdmin

import logging
from django.http import HttpResponse
from wsgiref.util import FileWrapper
import io
from django.contrib import messages
from django.conf import settings

from django.contrib.auth import get_user_model

from rdrf.admin_forms import ConsentConfigurationAdminForm, RegistryDashboardAdminForm, DashboardWidgetAdminForm
from rdrf.admin_forms import RegistryFormAdminForm
from rdrf.admin_forms import EmailTemplateAdminForm
from rdrf.admin_forms import DemographicFieldsAdminForm
from rdrf.admin_forms import CommonDataElementAdminForm
from rdrf.admin_forms import ContextFormGroupItemAdminForm
from rdrf.admin_forms import FormTitleAdminForm
from rdrf.admin_forms import BlacklistedMimeTypeAdminForm

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
    search_fields = ['name']

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


def export_registry_action(modeladmin, request, registry_models_selected):
    from datetime import datetime
    export_time = str(datetime.now())

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

    registrys = list(registry_models_selected)

    if len(registrys) == 1:
        registry = registrys[0]
        yaml_export_filename = registry.name + ".yaml"
        yaml_data = export_registry(registry, request)
        if yaml_data is None:
            return

        myfile = io.StringIO()
        myfile.write(yaml_data)
        myfile.flush()
        myfile.seek(0)

        response = HttpResponse(FileWrapper(myfile), content_type='text/yaml')
        yaml_export_filename = "export_%s_%s" % (export_time, yaml_export_filename)
        response['Content-Disposition'] = 'attachment; filename="%s"' % yaml_export_filename

        return response
    else:
        import zipfile
        zippedfile = io.BytesIO()
        zf = zipfile.ZipFile(zippedfile, mode='w', compression=zipfile.ZIP_DEFLATED)

        for registry in registrys:
            yaml_data = export_registry(registry, request)
            if yaml_data is None:
                return

            zf.writestr(registry.code + '.yaml', yaml_data)

        zf.close()
        zippedfile.flush()
        zippedfile.seek(0)

        response = HttpResponse(FileWrapper(zippedfile), content_type='application/zip')
        name = "export_" + export_time + "_" + \
            reduce(lambda x, y: x + '_and_' + y, [r.code for r in registrys]) + ".zip"
        response['Content-Disposition'] = 'attachment; filename="%s"' % name

        return response


export_registry_action.short_description = "Export"


def generate_questionnaire_action(modeladmin, request, registry_models_selected):
    for registry in registry_models_selected:
        registry.generate_questionnaire()


generate_questionnaire_action.short_description = _("Generate Questionnaire")


class RegistryAdmin(admin.ModelAdmin):
    actions = [export_registry_action, generate_questionnaire_action]

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
    form = ConsentConfigurationAdminForm
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


class BlacklistedMimeTypeAdmin(admin.ModelAdmin):
    model = BlacklistedMimeType
    form = BlacklistedMimeTypeAdminForm
    list_display = ('mime_type', 'description')


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


class DashboardDemographicsInline(admin.StackedInline):
    model = RegistryDashboardDemographicData
    verbose_name_plural = 'Patient Demographics'
    extra = 0


class RegistryDashboardAdmin(admin.ModelAdmin):
    model = RegistryDashboard
    form = RegistryDashboardAdminForm
    list_display = ('registry',)


class DashboardWidgetAdmin(admin.ModelAdmin):
    model = RegistryDashboardWidget
    form = DashboardWidgetAdminForm
    list_display = ('registry_dashboard', 'widget_type', 'title')
    list_select_related = ('registry_dashboard',)
    list_filter = ['registry_dashboard']
    inlines = [DashboardLinksInline, DashboardDemographicsInline, DashboardCdeDataInline]


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
    (BlacklistedMimeType, BlacklistedMimeTypeAdmin),
    (Section, SectionAdmin),
    (ConsentSection, ConsentSectionAdmin),
    (CdePolicy, CdePolicyAdmin),
    (ContextFormGroup, ContextFormGroupAdmin),
    (CDEFile, CDEFileAdmin),
    (RegistryDashboard, RegistryDashboardAdmin),
    (RegistryDashboardWidget, DashboardWidgetAdmin),
]

NORMAL_MODE_ADMIN_COMPONENTS = [
    (Registry, RegistryAdmin),
    (QuestionnaireResponse, QuestionnaireResponseAdmin),
    (EmailNotification, EmailNotificationAdmin),
    (EmailTemplate, EmailTemplateAdmin),
    (EmailNotificationHistory, EmailNotificationHistoryAdmin),
    (Notification, NotificationAdmin),
    (DemographicFields, DemographicFieldsAdmin),
    (ConsentRule, ConsentRuleAdmin),
    (FormTitle, FormTitleAdmin),
    (BlacklistedMimeType, BlacklistedMimeTypeAdmin),
]

ADMIN_COMPONENTS = NORMAL_MODE_ADMIN_COMPONENTS

if settings.DESIGN_MODE:
    ADMIN_COMPONENTS += DESIGN_MODE_ADMIN_COMPONENTS

for model_class, model_admin in ADMIN_COMPONENTS:
    if not admin.site.is_registered(model_class):
        admin.site.register(model_class, model_admin)

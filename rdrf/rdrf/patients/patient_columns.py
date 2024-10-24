import logging

from django.template import Context, loader
from django.urls import reverse
from django.utils.formats import date_format

from rdrf.forms.components import FormGroupButton
from rdrf.helpers.registry_features import RegistryFeatures

logger = logging.getLogger(__name__)


class Column(object):
    field = "id"
    sort_fields = ["id"]
    visible = True

    def __init__(self, label, perm):
        self.label = label
        self.perm = perm

    def configure(self, registry, user, order):
        self.registry = registry
        self.user = user
        self.order = order
        self.user_can_see = user.has_perm(self.perm)

    def cell(
        self,
        patient,
        supports_contexts=False,
        form_progress=None,
        context_manager=None,
    ):
        if "__" in self.field:
            patient_field, related_object_field = self.field.split("__")
            related_object = getattr(patient, patient_field)
            if related_object.__class__.__name__ == "ManyRelatedManager":
                return ", ".join(
                    list(
                        related_object.values_list(
                            related_object_field, flat=True
                        )
                    )
                )

            if related_object is not None:
                related_value = getattr(related_object, related_object_field)
            else:
                related_value = None
            return related_value
        return getattr(patient, self.field)

    def fmt(self, val):
        return str(val)

    def to_dict(self, i):
        "Structure used by jquery datatables"
        return {
            "data": self.field,
            "label": self.label,
            "visible": self.visible,
            "orderable": len(self.sort_fields) > 0,
            "order": i,
        }


class ColumnFullName(Column):
    field = "full_name"
    sort_fields = ["family_name", "given_names"]

    def configure(self, registry, user, order):
        super(ColumnFullName, self).configure(registry, user, order)
        if not registry:
            return "<span>%d %s</span>"

        # cache reversed url because urlroute searches are slow
        base_url = reverse(
            "patient_edit",
            kwargs={"registry_code": registry.code, "patient_id": 0},
        )
        self.link_template = '<a href="%s">%%s</a>' % (
            base_url.replace("/0", "/%d")
        )

    def cell(
        self,
        patient,
        supports_contexts=False,
        form_progress=None,
        context_manager=None,
    ):
        return self.link_template % (patient.id, patient.display_name)


class ColumnDateOfBirth(Column):
    field = "date_of_birth"
    sort_fields = ["date_of_birth"]

    def fmt(self, val):
        return date_format(val, "d-m-Y") if val is not None else ""


class ColumnCodeField(Column):
    field = "code_field"
    sort_fields = ["sex", "patient_type"]


class ColumnOptionalContext(Column):
    sort_fields = []

    def cell(
        self,
        patient,
        supports_contexts=False,
        form_progress=None,
        context_manager=None,
    ):
        return self.cell_optional_contexts(
            patient, form_progress, context_manager
        )

    def fmt(self, val):
        return (
            self.icon(None) if val is None else self.fmt_optional_contexts(val)
        )

    def cell_optional_contexts(
        self, patient, form_progress=None, context_manager=None
    ):
        pass

    def fmt_optional_contexts(self, val):
        return val

    def icon(self, tick):
        icon = "check" if tick else "times"
        color = "green" if tick else "red"
        # fixme: replace inline style with css class
        return "<span class='fa fa-%s' style='color:%s'></span>" % (icon, color)


class ColumnWorkingGroups(Column):
    field = "working_groups__name"
    sort_fields = ["working_groups__name"]


class ColumnDiagnosisProgress(ColumnOptionalContext):
    field = "diagnosis_progress"

    def cell_optional_contexts(
        self, patient, form_progress=None, context_manager=None
    ):
        default_ctx = (
            context_manager.get_or_create_default_context(patient)
            if context_manager
            else None
        )
        return form_progress.get_group_progress(
            "diagnosis", patient, default_ctx
        )

    def fmt_optional_contexts(self, progress_number):
        template = (
            "<div class='progress'><div class='progress-bar progress-bar-custom' role='progressbar'"
            " aria-valuenow='%s' aria-valuemin='0' aria-valuemax='100' style='width: %s%%'>"
            "<span class='progress-label'>%s%%</span></div></div>"
        )
        return template % (progress_number, progress_number, progress_number)


class ColumnDiagnosisCurrency(ColumnOptionalContext):
    field = "diagnosis_currency"
    sort_fields = ["last_updated_overall_at"]

    def cell_optional_contexts(
        self, patient, form_progress=None, context_manager=None
    ):
        default_ctx = (
            context_manager.get_or_create_default_context(patient)
            if context_manager
            else None
        )
        return form_progress.get_group_currency(
            "diagnosis", patient, default_ctx
        )

    def fmt_optional_contexts(self, diagnosis_currency):
        return self.icon(diagnosis_currency)


class ColumnPatientStage(Column):
    field = "stage"
    sort_fields = ["stage__id"]

    def fmt(self, val):
        if self.registry and self.registry.has_feature(RegistryFeatures.STAGES):
            return str(val)
        return "N/A"


class ColumnContextMenu(Column):
    field = "context_menu"
    sort_fields = []

    def _has_visible_forms(self, user, cfg):
        for form in cfg.forms:
            if user.can_view(form):
                return True

        return False

    def configure(self, registry, user, order):
        super(ColumnContextMenu, self).configure(registry, user, order)
        self.registry_has_context_form_groups = (
            registry.has_groups if registry else False
        )

        if registry:
            # fixme: slow, do intersection instead
            self.free_forms = list(filter(user.can_view, registry.free_forms))
            self.fixed_form_groups = [
                group
                for group in registry.fixed_form_groups
                if self._has_visible_forms(user, group)
            ]
            self.multiple_form_groups = [
                group
                for group in registry.multiple_form_groups
                if self._has_visible_forms(user, group)
            ]

    def cell(
        self,
        patient,
        supports_contexts=False,
        form_progress=None,
        context_manager=None,
    ):
        return " ".join(self._get_forms_buttons(patient))

    def _get_forms_buttons(
        self, patient, form_progress=None, context_manager=None
    ):
        if not self.registry_has_context_form_groups:
            # if there are no context groups -normal registry
            return [self._get_forms_button(patient, None, self.free_forms)]
        else:
            if (
                len(self.fixed_form_groups) == 0
                and len(self.multiple_form_groups) == 0
            ):
                return ["None"]

            # display one button per form group
            buttons = []
            for fixed_form_group in self.fixed_form_groups:
                buttons.append(
                    self._get_forms_button(
                        patient, fixed_form_group, fixed_form_group.forms
                    )
                )

            for multiple_form_group in self.multiple_form_groups:
                buttons.append(
                    self._get_forms_button(
                        patient, multiple_form_group, multiple_form_group.forms
                    )
                )
            return buttons

    def _get_forms_button(self, patient_model, context_form_group, forms):
        button = FormGroupButton(
            self.registry, self.user, patient_model, context_form_group
        )
        return button.html


class ColumnDateLastUpdated(Column):
    field = "last_updated_overall_at"
    sort_fields = ["last_updated_overall_at"]

    def fmt(self, val):
        return date_format(val, "d-m-Y") if val is not None else ""


class ColumnActionsMenu(Column):
    TEMPLATE = "rdrf_cdes/patient_listing_actions.html"

    def _template_data(self, patient):
        return {
            "patient": patient,
            "archive_patient_url": patient.get_archive_url(self.registry)
            if self.user.can_archive
            else "",
            "not_linked": not patient.is_linked,
        }

    def fmt(self, val):
        template = loader.get_template(self.TEMPLATE)
        data = self._template_data(val)
        context = Context(data)
        return template.render(context.flatten())

    def cell(
        self,
        patient,
        supports_contexts=False,
        form_progress=None,
        context_manager=None,
    ):
        return patient

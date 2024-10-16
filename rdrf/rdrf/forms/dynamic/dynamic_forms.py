import logging
from collections import OrderedDict
from datetime import datetime as dt

from django.conf import settings
from django.forms import BaseForm
from django.utils.formats import date_format

from rdrf.forms.dynamic.field_lookup import FieldFactory
from rdrf.helpers.cde_data_types import CDEDataTypes
from rdrf.models.definition.models import CommonDataElement

logger = logging.getLogger(__name__)


def create_form_class(owner_class_name):
    form_class_name = "CDEForm"
    cde_map = {}
    base_fields = {}

    for cde in CommonDataElement.objects.all().filter(owner=owner_class_name):
        cde_field = FieldFactory(cde).create_field()
        field_name = cde.code
        # e.g.  "CDE0023" --> the cde element corresponding to this code
        cde_map[field_name] = cde
        base_fields[field_name] = cde_field  # a django field object

    class Media:
        css = {"all": ("dmd_admin.css",)}

    form_class_dict = {
        "base_fields": base_fields,
        "cde_map": cde_map,
        "Media": Media,
    }

    form_class = type(form_class_name, (BaseForm,), form_class_dict)
    return form_class


def create_form_class_for_section(
    registry,
    data_defs,
    registry_form,
    section,
    injected_model=None,
    injected_model_id=None,
    is_superuser=None,
    user_groups=None,
    patient_model=None,
    allowed_cdes=(),
    previous_values=None,
):
    def format_date(input):
        # Transform date from YYYY-MM-DD to DD-MM-YYYY
        if not input:
            return
        # TODO: python 3.7 re-write to use date.fromisoformat(input)
        as_date = dt.strptime(input, "%Y-%m-%d")
        return date_format(as_date, format="d-m-Y")

    if previous_values is None:
        previous_values = {}

    cde_codes = section.get_elements()
    cde_models = [data_defs.form_cdes[cde_code] for cde_code in cde_codes]

    if allowed_cdes:
        cde_models = (c for c in cde_models if c.code in allowed_cdes)
    base_fields = OrderedDict()
    for cde in cde_models:
        cde_policy = data_defs.cde_policies.get(cde.code)
        if cde_policy and user_groups:
            if not cde_policy.is_allowed(
                user_groups.all(), patient_model, is_superuser=is_superuser
            ):
                continue

        cde_field = FieldFactory(
            registry,
            data_defs,
            registry_form,
            section,
            cde,
            injected_model=injected_model,
            injected_model_id=injected_model_id,
            is_superuser=is_superuser,
        ).create_field()

        cde_field.important = cde.important
        prev_value = previous_values.get(cde.code)
        if section.allow_multiple and section.code in previous_values:
            prev_value = [
                v
                for x in previous_values[section.code]
                for k, v in x.items()
                if k.endswith(cde.code)
            ]

        cde_field.previous_value = prev_value
        if prev_value and cde.pv_group:
            values = {
                el["code"].lower(): el["value"]
                for el in cde.pv_group.as_dict["values"]
            }
            if isinstance(prev_value, list):
                cde_field.previous_value = [
                    values.get(v.lower()) for v in prev_value
                ]
            else:
                cde_field.previous_value = values.get(prev_value.lower())

        if cde.datatype == CDEDataTypes.DATE and cde_field.previous_value:
            previous = cde_field.previous_value
            is_list = isinstance(previous, list)
            cde_field.previous_value = (
                [format_date(el) for el in previous]
                if is_list
                else format_date(previous)
            )

        field_code_on_form = "%s%s%s%s%s" % (
            registry_form.name,
            settings.FORM_SECTION_DELIMITER,
            section.code,
            settings.FORM_SECTION_DELIMITER,
            cde.code,
        )
        base_fields[field_code_on_form] = cde_field

    form_class_dict = {"base_fields": base_fields, "auto_id": True}

    return (
        type("SectionForm", (BaseForm,), form_class_dict)
        if base_fields
        else None
    )

import logging

from django import forms
from django.db.models import Count, F

logger = logging.getLogger(__name__)


def _working_group_types(wg_queryset):
    return (
        wg_queryset.values("type")
        .annotate(name=F("type__name"), aggregate_by_count=Count("type"))
        .order_by("type__name")
    )


def working_group_fields(wg_queryset, initial):
    def filter_queryset_by_type(queryset, working_group_type):
        return queryset.filter(type=working_group_type)

    def working_group_choices(queryset):
        return [(wg.id, wg.display_name) for wg in queryset]

    base_choices = working_group_choices(
        filter_queryset_by_type(wg_queryset, None)
    )

    additional_fields = {
        f"working_groups_{working_group_type['type']}": forms.MultipleChoiceField(
            label=working_group_type["name"],
            choices=working_group_choices(
                filter_queryset_by_type(wg_queryset, working_group_type["type"])
            ),
            initial=[
                wg.id
                for wg in filter_queryset_by_type(
                    initial, working_group_type["type"]
                )
            ],
        )
        for working_group_type in _working_group_types(wg_queryset)
        if working_group_type["type"]
    }

    return base_choices, additional_fields


def working_group_optgroup_choices(wg_queryset, make_option_fn=None):
    def default_make_option_fn(working_group):
        # e.g. <option value="{{working_group.id}}">{{working_group}}</option>
        return working_group.id, working_group.display_name

    make_option_fn = make_option_fn or default_make_option_fn
    return [
        (
            wg_type.get("name"),
            [
                make_option_fn(wg)
                for wg in wg_queryset.filter(type=wg_type.get("type"))
            ],
        )
        for wg_type in (_working_group_types(wg_queryset))
    ]

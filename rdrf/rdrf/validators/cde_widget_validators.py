from django.forms import ValidationError
from django.utils.translation import gettext as _

from rdrf.models.definition.models import CDEPermittedValue


class OtherPleaseSpecifyWidgetValidator:

    def __init__(self, cleaned_data):
        self.cleaned_data = cleaned_data

    def validate(self):
        pv_group = self.cleaned_data.get('pv_group')
        widget_name = self.cleaned_data.get('widget_name')
        if not pv_group:
            raise ValidationError({
                "pv_group": [_(f"{widget_name} widget needs a pv group to be specified !!")]
            })
        values = pv_group.members(get_code=False)
        valid_pv_group = any([v.lower().find('specify') > -1 for v in values])
        if not valid_pv_group:
            valid_groups_qs = CDEPermittedValue.objects.filter(value__icontains='specify').values_list('pv_group', flat=True)
            valid_groups = [g for g in valid_groups_qs]
            if not valid_groups:
                raise ValidationError({
                    "pv_group": [_("There are no valid pv groups for {widget_name} widget ! A valid pv_group must contain a value with the text 'specify'")]
                })
            else:
                raise ValidationError({
                    "pv_group": [_(f"The pv group is invalid ! Valid groups are: {valid_groups}")]
                })

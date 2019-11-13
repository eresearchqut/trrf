# Custom validators for different widget settings in common data element
import json

from django.forms import ValidationError
from django.utils.translation import gettext as _

from rdrf.forms.widgets.settings_widgets import SliderWidgetSettings, TimeWidgetSettings


class BaseValidator:

    def __init__(self, widget, cleaned_data):
        self.cleaned_data = cleaned_data
        self.widget = widget
        self.settings = {}

    def validate_json(self):
        data = self.cleaned_data['widget_settings'] or '{}'
        try:
            self.settings = json.loads(data)
        except Exception:
            raise ValidationError(_('Widget settings must be a valid JSON!'))
        unknown_fields = self.settings.keys() - self.widget.get_allowed_fields()
        if unknown_fields:
            raise ValidationError(_('Invalid fields in JSON: {fields}').format(fields=', '.join(unknown_fields)))

    def validate(self):
        self.validate_json()


class SliderWidgetSettingsValidator(BaseValidator):

    def validate(self):
        super().validate()
        cde_datatype = self.cleaned_data['datatype']
        cde_min_value = self.cleaned_data['min_value']
        cde_max_value = self.cleaned_data['max_value']

        def parse_number(field):
            if field not in self.settings:
                return None
            try:
                if cde_datatype == 'float':
                    return float(self.settings[field])
                if cde_datatype == 'integer':
                    return int(self.settings[field])
            except ValueError:
                raise ValidationError(_('{field} must be {data_type}. Invalid value: {value}').format(
                    data_type=cde_datatype, field=field, value=self.settings[field]))

        min_value = parse_number('min')
        max_value = parse_number('max')
        step = parse_number('step')

        if cde_min_value is None and min_value is None:
            raise ValidationError(_('You must supply the widget setting Min value if the CDE Min value is not set'))

        if cde_max_value is None and max_value is None:
            raise ValidationError(_('You must supply the widget setting Max value if the CDE Max value is not set'))

        if min_value is not None and cde_min_value is not None:
            if min_value < cde_min_value:
                raise ValidationError(_("Min value must be bigger or equal than CDE's min value!"))

        if max_value is not None and cde_max_value is not None:
            if max_value > cde_max_value:
                raise ValidationError(_("Max value must be lower or equal than CDE's max value!"))

        if min_value is not None and max_value is not None:
            if max_value <= min_value:
                raise ValidationError(_('Max value should be bigger than Min value'))

        if step is not None:
            overall_min_value = cde_min_value if min_value is None else min_value
            overall_max_value = cde_max_value if max_value is None else max_value
            if step >= overall_max_value - overall_min_value:
                raise ValidationError(_('Step value too large for Min value and Max value'))


class TimeWidgetSettingsValidator(BaseValidator):

    def validate(self):
        super().validate()
        if 'format' not in self.settings:
            raise ValidationError(_("The format must be specified for time widget settings !"))


def get_validator(widget_instance, cleaned_data):
    if isinstance(widget_instance, TimeWidgetSettings):
        return TimeWidgetSettingsValidator(widget_instance, cleaned_data)
    if isinstance(widget_instance, SliderWidgetSettings):
        return SliderWidgetSettingsValidator(widget_instance, cleaned_data)
    return None

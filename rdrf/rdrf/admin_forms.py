from functools import reduce
import json
import logging
import re

from django.conf import settings
from django.forms import ModelForm, SelectMultiple, ChoiceField, ValidationError, HiddenInput
from django.utils.translation import gettext as _

from rdrf.models.definition.models import RegistryForm, CommonDataElement, Section, DemographicFields
from rdrf.models.definition.models import EmailTemplate, ConsentConfiguration
from rdrf.forms.widgets.widgets import SliderWidgetSettings, TimeWidgetSettings
from registry.patients.models import Patient


from rdrf.helpers.constants import (
    PATIENT_ADDRESS_SECTION_NAME, PATIENT_DOCTOR_SECTION_NAME,
    PATIENT_NEXT_OF_KIN_SECTION_NAME, PATIENT_STAGE_SECTION_NAME,
    PATIENT_RELATIVE_SECTION_NAME
)

logger = logging.getLogger(__name__)


class RegistryFormAdminForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs:
            instance = kwargs["instance"]
            if instance is not None:
                sections = Section.objects.get_by_comma_separated_codes(kwargs['instance'].sections)
                available_cdes = reduce(set.union, (section.get_elements() for section in sections), set())

                complete_form_cdes = set(instance.complete_form_cdes.values_list('code', flat=True))

                all_cdes = available_cdes.union(complete_form_cdes)

                self.fields['complete_form_cdes'].queryset = CommonDataElement.objects.filter(
                    code__in=all_cdes)

    def clean_sections(self):
        data = self.cleaned_data['sections']
        codes = [s.strip() for s in data.split(',')]
        existing_codes = Section.objects.filter(code__in=codes).values_list('code', flat=True)
        if len(codes) != len(existing_codes):
            missing_codes = ', '.join(c for c in codes if c not in set(existing_codes))
            raise ValidationError(f'Invalid section codes: {missing_codes}')
        return self.cleaned_data['sections']

    def clean(self):
        if 'sections' in self.cleaned_data and 'complete_form_cdes' in self.cleaned_data:
            self.instance._check_completion_cdes(
                self.cleaned_data['complete_form_cdes'],
                self.cleaned_data['sections'])

    class Meta:
        model = RegistryForm
        fields = "__all__"
        widgets = {
            'complete_form_cdes': SelectMultiple(attrs={'size': 20, 'style': 'width:50%'})
        }


class DemographicFieldsAdminForm(ModelForm):

    SECTION_PREFIX = "SECTION:"

    @classmethod
    def section_name(cls, section):
        return f"{cls.SECTION_PREFIX}{section}"

    sections = [
        PATIENT_ADDRESS_SECTION_NAME, PATIENT_DOCTOR_SECTION_NAME, PATIENT_NEXT_OF_KIN_SECTION_NAME,
        PATIENT_STAGE_SECTION_NAME, PATIENT_RELATIVE_SECTION_NAME
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        non_required_patient_fields = [f for f in Patient._meta.fields if f.blank]

        field_choices = sorted([(self.section_name(s), f'{s} section') for s in self.sections])
        field_choices += sorted([(f.name, f.name) for f in non_required_patient_fields])

        self.fields['field'] = ChoiceField(
            choices=field_choices,
            help_text=_("Note: required fields aren't displayed as they can't be hidden or made read-only")
        )
        self.fields['is_section'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        field_value = cleaned_data.get('field')
        if field_value:
            result = re.match(f"(^{self.SECTION_PREFIX})(.+)", field_value)
            if result and result.groups()[1] in self.sections:
                cleaned_data['is_section'] = True
                if cleaned_data.get('status') == DemographicFields.READONLY:
                    raise ValidationError(
                        "You cannot set a section to read-only ! Only hidden sections are supported for now"
                    )
        return cleaned_data


class EmailTemplateAdminForm(ModelForm):
    """
    This form introduced so we can parametrise the languages list from settings.
    If we do this on the model it causes a migration fail in the build.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_choices = settings.LANGUAGES
        self.fields['language'] = ChoiceField(choices=field_choices)

    class Meta:
        fields = "__all__"
        model = EmailTemplate


class ConsentConfigurationAdminForm(ModelForm):

    class Meta:
        fields = "__all__"
        model = ConsentConfiguration


class CommonDataElementAdminForm(ModelForm):

    template = 'admin/cde_change_form.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget_name = self.data.get('widget_name', '') or self.instance.widget_name
        settings_dict = {
            'SliderWidget': lambda: SliderWidgetSettings(),
            'TimeWidget': lambda: TimeWidgetSettings(),
        }
        self.fields['widget_settings'].widget = settings_dict.get(widget_name, lambda: HiddenInput())()
        self.fields['widget_name'].widget.attrs = {'onchange': 'widgetNameChangeHandler()'}

    class Meta:
        fields = "__all__"
        model = CommonDataElement

    def clean_widget_settings(self):
        settings_widget = self.fields['widget_settings'].widget
        if not hasattr(settings_widget, 'get_allowed_fields'):
            return

        data = self.cleaned_data['widget_settings'] or '{}'
        settings = {}
        try:
            settings = json.loads(data)
        except Exception:
            raise ValidationError(_('Widget settings must be a valid JSON!'))

        allowed_fields = settings_widget.get_allowed_fields()
        unknown_fields = set(settings.keys()) - allowed_fields
        if unknown_fields:
            raise ValidationError(_('Invalid fields in JSON: {fields}').format(fields=', '.join(unknown_fields)))

        return data

    def _validate_slider_widget_settings(self, settings):
        cde_datatype = self.cleaned_data['datatype']
        cde_min_value = self.cleaned_data['min_value']
        cde_max_value = self.cleaned_data['max_value']

        def validation_error(msg):
            raise ValidationError({'widget_settings': msg})

        def parse_number(field):
            if field not in settings:
                return None
            try:
                if cde_datatype == 'float':
                    return float(settings[field])
                if cde_datatype == 'integer':
                    return int(settings[field])
            except ValueError:
                validation_error(_('{field} must be {data_type}. Invalid value: {value}').format(
                    data_type=cde_datatype, field=field, value=settings[field]))

        min_value = parse_number('min')
        max_value = parse_number('max')
        step = parse_number('step')

        if cde_min_value is None and min_value is None:
            validation_error(_('You must supply the widget setting Min value if the CDE Min value is not set'))

        if cde_max_value is None and max_value is None:
            validation_error(_('You must supply the widget setting Max value if the CDE Max value is not set'))

        if min_value is not None and cde_min_value is not None:
            if min_value < cde_min_value:
                validation_error(_("Min value must be bigger or equal than CDE's min value!"))

        if max_value is not None and cde_max_value is not None:
            if max_value > cde_max_value:
                validation_error(_("Max value must be lower or equal than CDE's max value!"))

        if min_value is not None and max_value is not None:
            if max_value <= min_value:
                validation_error(_('Max value should be bigger than Min value'))

        if step is not None:
            overall_min_value = cde_min_value if min_value is None else min_value
            overall_max_value = cde_max_value if max_value is None else max_value
            if step >= overall_max_value - overall_min_value:
                validation_error(_('Step value too large for Min value and Max value'))

    def _validate_time_widget_settings(self, settings):
        if 'format' not in settings:
            raise ValidationError({'widget_settings': _("The format must be specified for time widget settings !")})

    def _default_validate_widget_settings(self, settings):
        pass

    def _validate_widget_settings(self):
        widget_name = self.cleaned_data['widget_name']
        validators = {
            'SliderWidget': self._validate_slider_widget_settings,
            'TimeWidget': self._validate_time_widget_settings
        }
        validator = validators.get(widget_name, self._default_validate_widget_settings)
        cleaned_settings = self.cleaned_data.get('widget_settings')
        if not cleaned_settings:
            self.cleaned_data['widget_settings'] = '{}'
        settings = json.loads(self.cleaned_data['widget_settings'])
        validator(settings)

    def clean(self):
        if self.cleaned_data['widget_name'] == 'SliderWidget' and self.cleaned_data['datatype'] not in ('integer', 'float'):
            raise ValidationError(_('SliderWidget can be used only with CDEs of datatype "integer" or "float"'))

        self._validate_widget_settings()

from functools import reduce
import logging
import re

from django.conf import settings
from django.forms import ModelForm, SelectMultiple, ChoiceField, ValidationError, HiddenInput, Select, Widget
from django.utils.translation import gettext as _

from rdrf.models.definition.models import RegistryForm, CommonDataElement, ContextFormGroupItem, Section, DemographicFields
from rdrf.models.definition.models import EmailTemplate, ConsentConfiguration, FormTitle
from rdrf.forms.widgets import widgets as rdrf_widgets
from rdrf.forms.widgets import settings_widgets
from registry.patients.models import Patient


from rdrf.helpers.constants import (
    PATIENT_ADDRESS_SECTION_NAME, PATIENT_DOCTOR_SECTION_NAME,
    PATIENT_NEXT_OF_KIN_SECTION_NAME, PATIENT_STAGE_SECTION_NAME,
    PATIENT_RELATIVE_SECTION_NAME
)

from rdrf.validators.cde_widget_settings_validators import get_validator
from rdrf.validators.cde_widget_validators import OtherPleaseSpecifyWidgetValidator

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
        widget_name = self.data.get('widget_name', self.instance.widget_name)
        data_type = self.data.get('datatype', self.instance.datatype)
        settings_dict = {
            'SliderWidget': lambda: settings_widgets.SliderWidgetSettings(),
            'TimeWidget': lambda: settings_widgets.TimeWidgetSettings(),
            'RadioSelect': lambda: settings_widgets.RadioSelectSettings(),
        }
        self.fields['widget_settings'].widget = settings_dict.get(widget_name, lambda: HiddenInput())()

        default_choice = ('', _("Default widget"))
        choices = [default_choice]
        if data_type:
            choices += [(name, name) for name in rdrf_widgets.get_widgets_for_data_type(data_type)]

        self.fields['widget_name'].widget = Select(choices=choices)
        self.fields['widget_name'].widget.attrs = {'onchange': 'widgetNameChangeHandler()'}
        self.fields['datatype'].widget.attrs = {'onchange': 'dataTypeChangeHandler()'}

    class Meta:
        fields = "__all__"
        model = CommonDataElement

    def clean_widget_name(self):
        widget_name = self.cleaned_data['widget_name']
        if not widget_name:
            return widget_name

        WidgetClass = getattr(rdrf_widgets, widget_name, object)
        if not issubclass(WidgetClass, Widget):
            raise ValidationError(_(f'Invalid widget "{widget_name}"'))

        return widget_name

    def clean_widget_settings(self):
        validator = get_validator(self.fields['widget_settings'].widget, self.cleaned_data)
        if validator:
            validator.validate()
        return self.cleaned_data['widget_settings']

    def clean(self):
        cleaned_data = super().clean()
        data_type = cleaned_data.get('datatype')
        widget_name = cleaned_data.get('widget_name')
        if widget_name:
            WidgetClass = getattr(rdrf_widgets, widget_name)
            if data_type not in WidgetClass.usable_for_types():
                raise ValidationError(_(f"{widget_name} widget not usable for datatype: {data_type} !"))
            if WidgetClass == rdrf_widgets.OtherPleaseSpecifyWidget:
                OtherPleaseSpecifyWidgetValidator(self.cleaned_data).validate()


class ContextFormGroupItemAdminForm(ModelForm):

    class Meta:
        model = ContextFormGroupItem
        fields = "__all__"

    def clean(self):
        cfg = self.cleaned_data['context_form_group']
        form = self.cleaned_data['registry_form']

        if cfg.registry != form.registry:
            raise ValidationError(_(f"Form's registry ({cfg.registry.code}) must be the same as the Context Form Group's registry ({form.registry.code})"))


class FormTitleAdminForm(ModelForm):

    def clean(self):
        reg = self.cleaned_data['registry']
        groups = self.cleaned_data['groups']
        default_title = self.cleaned_data['default_title']
        ft_qs = FormTitle.objects.filter(registry=reg, groups__in=groups, default_title=default_title)
        if self.instance and self.instance.pk:
            ft_qs = ft_qs.exclude(id=self.instance.pk)

        if ft_qs.exists():
            raise ValidationError(_("An entry for the current combination of groups and default title already exists!"))

    class Meta:
        fields = "__all__"
        model = FormTitle

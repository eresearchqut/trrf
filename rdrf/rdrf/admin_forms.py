import re

from django.conf import settings
from django.forms import ModelForm, SelectMultiple, ChoiceField, ValidationError

from rdrf.models.definition.models import RegistryForm, CommonDataElement, Section, DemographicFields
from rdrf.models.definition.models import EmailTemplate
from registry.patients.models import Patient


class RegistryFormAdminForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(RegistryFormAdminForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            instance = kwargs["instance"]
            if instance is not None:
                sections = Section.objects.filter(
                    code__in=kwargs['instance'].sections.split(","))
                cdes = []
                for section in sections:
                    cdes += section.get_elements()
                self.fields['complete_form_cdes'].queryset = CommonDataElement.objects.filter(
                    code__in=cdes)

    def clean_sections(self):
        data = self.cleaned_data['sections']
        codes = [s.strip() for s in data.split(',')]
        existing_codes = Section.objects.filter(code__in=codes).values_list('code', flat=True)
        if len(codes) != len(existing_codes):
            missing_codes = ', '.join(c for c in codes if c not in set(existing_codes))
            raise ValidationError(f'Invalid section codes: {missing_codes}')
        return self.cleaned_data['sections']

    def clean(self):
        if 'sections' in self.cleaned_data:
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

    sections = ["Next of Kin", "Patient Address"]

    def __init__(self, *args, **kwargs):
        super(DemographicFieldsAdminForm, self).__init__(*args, **kwargs)

        patient_fields = Patient._meta.fields
        field_choices = []
        for patient_field in patient_fields:
            field_choices.append((patient_field.name, patient_field.name))

        for s in self.sections:
            field_choices.append((f"{DemographicFields.SECTION_PREFIX}{s}", f"{s} section"))

        field_choices.sort()
        self.fields['field'] = ChoiceField(choices=field_choices)

    def clean(self):
        cleaned_data = super().clean()
        field_value = cleaned_data.get('field')
        if field_value:
            result = re.match(f"(^{DemographicFields.SECTION_PREFIX})(.+)", field_value)
            if result and result.groups()[1] in self.sections:
                cleaned_data['is_section'] = True
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

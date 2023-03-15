import json

from django.contrib.auth.models import Group
from django.db.models.functions import Lower
from django.forms import SelectMultiple, ModelChoiceField, MultipleChoiceField, ChoiceField, CheckboxSelectMultiple, \
    Select, ModelForm, BooleanField
from django.utils.translation import gettext_lazy as _

from rdrf.helpers.utils import mongo_key
from rdrf.models.definition.models import ConsentQuestion, RegistryForm, Registry, ContextFormGroup
from registry.groups import PATIENT_OR_CAREGIVER_GROUPS
from registry.groups.models import WorkingGroup
from report.models import ReportClinicalDataField, ReportDemographicField, ReportDesign
from report.utils import load_report_configuration


def get_demographic_field_value(model_name, field):
    return json.dumps({"model": model_name, "field": field})


def get_demographic_field_choices(cfg_demographic_model):
    demographic_fields = []
    for model, model_attrs in cfg_demographic_model.items():
        field_choices = [(get_demographic_field_value(model, key), value) for key, value in model_attrs['fields'].items()]
        demographic_fields.append((model_attrs['label'], field_choices))
    return demographic_fields


def get_cde_field_value(context_form_group, cde_key):
    return json.dumps({'cfg': context_form_group.id, 'cde_key': cde_key})


def get_cde_choices():
    return [(get_cde_field_value(cfg, mongo_key(form.name, section.code, cde.code)), cde.name)
            for cfg in ContextFormGroup.objects.all()
            for form in cfg.forms
            for section in form.section_models
            for cde in section.cde_models]


def get_section_choices():
    def get_field_value(form, section):
        return json.dumps({'registry': form.registry.code, 'form': form.name, 'section': section.display_name})

    fields = [("", "Show all Clinical Data Fields")]

    fields.extend([
        (form.name, [(get_field_value(form, section), section.display_name if section.display_name.strip() else 'Form')
                     for section in form.section_models])
        for form in RegistryForm.objects.all()])

    return fields


def get_working_group_field_value(wg):
    return json.dumps({'registry': wg.registry.code if wg.registry else '',
                       'wg': wg.id})


def get_working_group_choices():
    return [(get_working_group_field_value(wg), wg.display_name) for wg in WorkingGroup.objects.all()]


def get_filter_consent_field_value(consent_question):
    return json.dumps({'registry': consent_question.section.registry.code, 'consent_question': consent_question.id})


def get_filter_consent_choices():
    return [(get_filter_consent_field_value(consent_question), consent_question.question_label)
            for consent_question in ConsentQuestion.objects.all().order_by('position')]


class ReportDesignerForm(ModelForm):

    registry = ModelChoiceField(label=_('Registry'), widget=Select(attrs={'class': 'form-select'}), queryset=Registry.objects.all(), to_field_name='code')
    demographic_fields = MultipleChoiceField(label=_('Demographic Fields'), required=False)
    search_cdes_by_section = ChoiceField(label=_('Filter fields by section'), widget=Select(attrs={'class': 'form-select'}), required=False)
    cde_fields = MultipleChoiceField(label=_('Fields'), required=False)
    filter_by_consents = BooleanField(label=_('Filter patients by consents'), required=False)
    filter_consents = MultipleChoiceField(
        label=_('Consent Items'),
        widget=CheckboxSelectMultiple,
        required=False)
    filter_by_working_groups = BooleanField(label=_('Filter patients by working group'), required=False)
    filter_working_groups = MultipleChoiceField(
        label=_('Working groups'),
        widget=SelectMultiple(attrs={'class': 'form-select'}),
        required=False)

    def __init__(self, *args, **kwargs):
        def init_report_configuration():
            return load_report_configuration()['demographic_model']

        super(ReportDesignerForm, self).__init__(*args, **kwargs)
        report_configuration = init_report_configuration()

        # Initialise choices during object initialisation to avoid compilation errors
        # when attempting to modify the models that are queried to build these choices.
        self.fields['demographic_fields'].choices = get_demographic_field_choices(report_configuration)
        self.fields['search_cdes_by_section'].choices = get_section_choices()
        self.fields['cde_fields'].choices = get_cde_choices()
        self.fields['filter_consents'].choices = get_filter_consent_choices()
        self.fields['filter_working_groups'].choices = get_working_group_choices()
        self.fields['access_groups'].queryset = Group.objects\
            .annotate(iname=Lower('name'))\
            .exclude(iname__in=[name.lower() for name in PATIENT_OR_CAREGIVER_GROUPS])\
            .order_by('name')

    class Meta:
        model = ReportDesign
        fields = [
            'id',
            'title',
            'description',
            'access_groups',
            'cde_heading_format',
            'cde_include_form_timestamp'
        ]
        labels = {
            'title': _('Title'),
            'description': _('Description'),
            'access_groups': _('Access Groups'),
            'cde_heading_format': _('Heading Format'),
            'cde_include_form_timestamp': _('Include Form Last Updated Timestamp in extract')
        }

    def setup_initials(self):
        if self.instance.id:
            self.fields['registry'].initial = self.instance.registry.code if self.instance.registry else None
            self.fields['demographic_fields'].initial = [get_demographic_field_value(rdf.model, rdf.field) for rdf in self.instance.reportdemographicfield_set.all()]
            self.fields['cde_fields'].initial = [get_cde_field_value(rcf.context_form_group, rcf.cde_key) for rcf in self.instance.reportclinicaldatafield_set.all()]
            self.fields['filter_by_consents'].initial = self.instance.filter_consents.count() > 0
            self.fields['filter_consents'].initial = [get_filter_consent_field_value(consent) for consent in self.instance.filter_consents.all()]
            self.fields['filter_by_working_groups'].initial = self.instance.filter_working_groups.count() > 0
            self.fields['filter_working_groups'].initial = [get_working_group_field_value(wg) for wg in self.instance.filter_working_groups.all()]

    def clean(self):
        super(ReportDesignerForm, self).clean()
        cleaned_title = self.cleaned_data.get('title', '')
        if not self.instance.id or self.instance.title != cleaned_title:
            if ReportDesign.objects.filter(registry=self.cleaned_data['registry'], title=cleaned_title).first():
                self.add_error('title', _(f'A report in this registry with the title "{cleaned_title}" already exists.'))
        return self.cleaned_data

    def clean_filter_working_groups(self):
        def get_wg_from_field(field):
            field_dict = json.loads(field)
            return WorkingGroup.objects.get(id=field_dict['wg'])

        return [get_wg_from_field(field) for field in self.cleaned_data['filter_working_groups']]

    def clean_filter_consents(self):
        def get_consent_from_field(field):
            field_dict = json.loads(field)
            return ConsentQuestion.objects.get(id=field_dict['consent_question'])

        return [get_consent_from_field(field) for field in self.cleaned_data['filter_consents']]

    def save_to_model(self):

        clean_data = self.cleaned_data

        report_design, created = ReportDesign.objects.update_or_create(
            id=self.instance.id,
            defaults={'title': clean_data['title'],
                      'description': clean_data['description'],
                      'registry': clean_data['registry'],
                      'cde_heading_format': clean_data['cde_heading_format'],
                      'cde_include_form_timestamp': clean_data['cde_include_form_timestamp']}
        )

        report_design.access_groups.set(clean_data['access_groups'])

        if clean_data['filter_by_working_groups']:
            report_design.filter_working_groups.set(clean_data['filter_working_groups'])
        else:
            report_design.filter_working_groups.set([])

        if clean_data['filter_by_consents']:
            report_design.filter_consents.set(clean_data['filter_consents'])
        else:
            report_design.filter_consents.set([])

        ReportDemographicField.objects.filter(report_design=report_design).delete()
        for idx, field in enumerate(clean_data['demographic_fields']):
            field_dict = json.loads(field)
            ReportDemographicField.objects.create(
                model=field_dict['model'],
                field=field_dict['field'],
                sort_order=idx,
                report_design=report_design
            )

        ReportClinicalDataField.objects.filter(report_design=report_design).delete()
        for field in clean_data['cde_fields']:
            field_dict = json.loads(field)
            ReportClinicalDataField.objects.create(
                cde_key=field_dict['cde_key'],
                context_form_group=ContextFormGroup.objects.get(id=field_dict['cfg']),
                report_design=report_design
            )

        report_design.save()

        self.instance = report_design

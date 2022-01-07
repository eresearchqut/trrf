import json
import logging

from django.forms import ModelForm, Select, SelectMultiple, ChoiceField, ModelChoiceField, MultipleChoiceField, \
    CheckboxSelectMultiple
from django.utils.translation import ugettext_lazy as _

from rdrf.helpers.utils import mongo_key
from rdrf.models.definition.models import ConsentQuestion, Registry, RegistryForm
from registry.groups.models import WorkingGroup
from .models import Query, ReportDesign, ReportDemographicField, ReportClinicalDataField
from .report_configuration import REPORT_CONFIGURATION

logger = logging.getLogger(__name__)

class QueryForm(ModelForm):

    class Meta:
        model = Query
        fields = [
            'id',
            'title',
            'description',
            'registry',
            'access_group',
            'collection',
            'criteria',
            'projection',
            'aggregation',
            'mongo_search_type',
            'sql_query',
            'max_items',
            'created_by'
        ]

# Reporting v2
def get_demographic_field_value(model_name, field):
    return json.dumps({"model": model_name, "field": field})

def get_demographic_field_choices():
    demographic_fields = []
    for model, model_attrs in REPORT_CONFIGURATION['demographic_model'].items():
        field_choices = [(get_demographic_field_value(model, value), key) for key, value in model_attrs['fields'].items()]
        demographic_fields.append((model, field_choices))
    return demographic_fields

def get_clinical_data_field_value(registry, cde_key):
    return json.dumps({'registry': registry.code, 'cde_key': cde_key})

def get_cde_choices():
    cde_fields = []
    for form in RegistryForm.objects.all():
        for section in form.section_models:
            form_section_cdes = [
                (get_clinical_data_field_value(form.registry, mongo_key(form.name, section.code, cde.code)), cde.name)
                for cde in section.cde_models
            ]
            cde_fields.append((f"{form.name} - {section.display_name}", form_section_cdes))

    return cde_fields

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
    return json.dumps({'registry': wg.registry.code, 'wg': wg.id})

def get_working_group_choices():
    return [(get_working_group_field_value(wg), wg.display_name) for wg in WorkingGroup.objects.all()]

def get_filter_consent_field_value(consent_question):
    return json.dumps({'registry': consent_question.section.registry.code, 'consent_question': consent_question.code})

def get_filter_consent_choices():
    return [(get_filter_consent_field_value(consent_question), consent_question.question_label)
            for consent_question in ConsentQuestion.objects.all().order_by('position')]


class ReportDesignerForm(ModelForm):

    registry = ModelChoiceField(label=_('Registry'), widget=Select(attrs={'class': 'form-select'}), queryset=Registry.objects.all(), to_field_name = 'code')
    demographic_fields = MultipleChoiceField(label=_('Demographic Fields'), widget=SelectMultiple(attrs={'class': 'form-select', 'size': '10'}), choices=get_demographic_field_choices())
    search_cdes_by_section = ChoiceField(label=_('Filter fields by section'), widget=Select(attrs={'class': 'form-select'}), choices=get_section_choices(), required=False)
    cde_fields = MultipleChoiceField(label=_('Clinical Data Fields'), widget=SelectMultiple(attrs={'class': 'form-select', 'size': '20'}), choices=get_cde_choices(), required=False)
    filter_consents = MultipleChoiceField(
        label=_('Consent Items'),
        widget=CheckboxSelectMultiple,
        choices=get_filter_consent_choices(),
        required=False)
    filter_working_groups =MultipleChoiceField(
        label=_('Working groups'),
        widget=SelectMultiple(attrs={'class': 'form-select'}),
        choices=get_working_group_choices(),
        required=False)

    class Meta:
        model = ReportDesign
        fields = [
            'id',
            'title',
            'description',
            'access_groups',
        ]
        widgets = {
            'access_groups': SelectMultiple(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': _('Title'),
            'description': _('Description'),
            'access_groups': _('Access Groups'),
        }

    def setup_initials(self):
        if self.instance.id:
            self.fields['registry'].initial = self.instance.registry.code if self.instance.registry else None
            self.fields['demographic_fields'].initial = [get_demographic_field_value(rdf.model, rdf.field) for rdf in self.instance.reportdemographicfield_set.all()]
            self.fields['cde_fields'].initial = [get_clinical_data_field_value(self.instance.registry, rcf.cde_key) for rcf in self.instance.reportclinicaldatafield_set.all()]
            self.fields['filter_consents'].initial = [get_filter_consent_field_value(consent) for consent in self.instance.filter_consents.all()]
            self.fields['filter_working_groups'].initial = [get_working_group_field_value(wg) for wg in self.instance.filter_working_groups.all()]

    def clean_filter_working_groups(self):
        def get_wg_from_field(field):
            field_dict = json.loads(field)
            return WorkingGroup.objects.get(id=field_dict['wg'])

        return [get_wg_from_field(field) for field in self.cleaned_data['filter_working_groups']]

    def clean_filter_consents(self):
        def get_consent_from_field(field):
            field_dict = json.loads(field)
            return ConsentQuestion.objects.get(code = field_dict['consent_question'])

        return [get_consent_from_field(field) for field in self.cleaned_data['filter_consents']]

    def save_to_model(self):

        clean_data = self.cleaned_data

        report_design, created = ReportDesign.objects.update_or_create(
            id=self.instance.id,
            defaults={'title': clean_data['title'],
                      'description': clean_data['description'],
                      'registry': clean_data['registry']}
        )

        report_design.access_groups.set(clean_data['access_groups'])
        report_design.filter_working_groups.set(clean_data['filter_working_groups'])
        report_design.filter_consents.set(clean_data['filter_consents'])

        ReportDemographicField.objects.filter(report_design=report_design).delete()
        for field in clean_data['demographic_fields']:
            field_dict = json.loads(field)
            ReportDemographicField.objects.create(
                model=field_dict['model'],
                field=field_dict['field'],
                report_design=report_design
            )

        ReportClinicalDataField.objects.filter(report_design=report_design).delete()
        for field in clean_data['cde_fields']:
            field_dict = json.loads(field)
            ReportClinicalDataField.objects.create(
                cde_key=field_dict['cde_key'],
                report_design=report_design
            )

        report_design.save()

        self.instance = report_design

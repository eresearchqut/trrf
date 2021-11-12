import json
import logging

from django.contrib.auth.models import Group
from django.forms import ModelForm, Select, SelectMultiple, MultipleChoiceField, ChoiceField, ModelMultipleChoiceField

from rdrf.models.definition.models import ConsentQuestion, Registry, RegistryForm
from registry.groups.models import WorkingGroup
from .models import Query, ReportDesign, DemographicField, CdeField
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

# Future State
def get_demographic_field_choices():
    def get_field_value(model_name, model_schema_lookup, field):
        return json.dumps({"model": model_name, "schema_lookup": model_schema_lookup, "field": field})

    demographic_fields = []
    for model, model_attrs in REPORT_CONFIGURATION['demographic_model'].items():
        field_choices = [(get_field_value(model, model_attrs['schema_lookup'], value), key) for key, value in model_attrs['fields'].items()]
        demographic_fields.append((model, field_choices))
    return demographic_fields

def get_cde_choices():

    def get_value(form, section, cde):
        return json.dumps({'registry': form.registry.code, 'form': form.name, 'section': section.code, 'cde': cde.code})

    cde_fields = []
    for form in RegistryForm.objects.all():
        for section in form.section_models:
            form_section_cdes = [(get_value(form, section, cde), cde.name) for cde in section.cde_models]
            cde_fields.append((f"{form.display_name} - {section.display_name}", form_section_cdes))

    return cde_fields

class ReportDesignerForm(ModelForm):

    demographic_fields = ChoiceField(widget=SelectMultiple(attrs={'class': 'form-select', 'size': '10'}), choices=get_demographic_field_choices())
    cde_fields = ChoiceField(widget=SelectMultiple(attrs={'class': 'form-select', 'size': '20'}), choices=get_cde_choices(), required=False)
    filter_consents = ModelMultipleChoiceField(queryset=ConsentQuestion.objects.all().order_by('position'))

    class Meta:
        model = ReportDesign
        fields = [
            'id',
            'title',
            'description',
            'registry',
            'access_groups',
            'filter_working_groups'
        ]
        widgets = {
            'registry': Select(attrs={'class': 'form-select'}),
            'access_groups': SelectMultiple(attrs={'class': 'form-select'}),
            'filter_working_groups': SelectMultiple(attrs={'class': 'form-select'})
        }

    def setup_initials(self):
        # TODO how to do this a better way without a setup method?
        if self.instance.id:
            self.fields['filter_consents'].initial = [consent.id for consent in self.instance.filter_consents.all()]
            self.fields['demographic_fields'].initial = [demo_field.field for demo_field in self.instance.demographicfield_set.all()]
            self.fields['cde_fields'].initial = [cde_field.field for cde_field in self.instance.cdefield_set.all()]

    def save_to_model(self):
        logger.info('!! DEBUG **')

        report_design, created = ReportDesign.objects.update_or_create(
            id=self.instance.id,
            defaults={'title': self.data['title'],
                      'description': self.data['description'],
                      'registry': Registry.objects.get(id=self.data['registry'])}
        )

        report_design.access_groups.set(Group.objects.filter(id__in=self.data.getlist('access_groups')))
        report_design.filter_working_groups.set(WorkingGroup.objects.filter(id__in=self.data.getlist('filter_working_groups')))
        report_design.filter_consents.set(ConsentQuestion.objects.filter(id__in=self.data.getlist('filter_consents')))

        demographic_fields = self.data.getlist('demographic_fields')
        DemographicField.objects.filter(report_design=report_design).delete()
        for field in demographic_fields:
            DemographicField.objects.create(
                field=field,
                report_design=report_design
            )

        cde_fields = self.data.getlist('cde_fields')
        CdeField.objects.filter(report_design=report_design).delete()
        for field in cde_fields:
            CdeField.objects.create(
                field=field,
                report_design=report_design
            )

        report_design.compile_query()
        # report_design.compiled_query = self.compile_to_query(report_design, demographic_fields)
        report_design.save()

        self.instance = report_design

        logger.info(f"save complete for report_design with id {report_design.id}")

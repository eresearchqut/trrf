import logging

import graphene
from graphene_django import DjangoObjectType
from graphene_django.debug import DjangoDebug

from rdrf.helpers.utils import mongo_key, get_form_section_code
from rdrf.models.definition.models import Registry, ConsentQuestion, ClinicalData, RDRFContext, ContextFormGroup, \
    Section, CommonDataElement, RegistryForm
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient, PatientAddress, AddressType, ConsentValue, NextOfKinRelationship

logger = logging.getLogger(__name__)

class ClinicalDataCdeInterface(graphene.Interface):
    code = graphene.String()
    name = graphene.String()

    @classmethod
    def resolve_type(self, instance, info):
        return ClinicalDataCdeMultiValue if type(instance['value']) is list else ClinicalDataCde

class ClinicalDataCde(graphene.ObjectType):
    class Meta:
        interfaces = (ClinicalDataCdeInterface,)

    value = graphene.String()

class ClinicalDataCdeMultiValue(graphene.ObjectType):
    class Meta:
        interfaces = (ClinicalDataCdeInterface,)

    values = graphene.List(graphene.String)

    def resolve_values(self, info):
        return self['value']

class ClinicalDataSection(graphene.ObjectType):
    code = graphene.String()
    name = graphene.String()
    entry_num = graphene.String()

class ContextFormGroupType(graphene.ObjectType):
    name = graphene.String()
    default_name = graphene.String()
    sort_order = graphene.String()
    entry_num = graphene.String()

class ClinicalDataType(graphene.ObjectType):
    cfg = graphene.Field(ContextFormGroupType)
    form = graphene.String()
    section = graphene.Field(ClinicalDataSection)
    cde = graphene.Field(ClinicalDataCdeInterface)

class PatientType(DjangoObjectType):
    sex = graphene.String()
    clinical_data = graphene.List(ClinicalDataType, cde_keys=graphene.List(graphene.String))

    class Meta:
        model = Patient
        fields = ('id','consent','consent_clinical_trials','consent_sent_information',
                  'consent_provided_by_parent_guardian','family_name','given_names','maiden_name','umrn',
                  'date_of_birth','date_of_death','place_of_birth','date_of_migration','country_of_birth',
                  'ethnic_origin','sex','home_phone','mobile_phone','work_phone','email','next_of_kin_family_name',
                  'next_of_kin_given_names','next_of_kin_relationship','next_of_kin_address','next_of_kin_suburb',
                  'next_of_kin_state','next_of_kin_postcode','next_of_kin_home_phone','next_of_kin_mobile_phone',
                  'next_of_kin_work_phone','next_of_kin_email','next_of_kin_parent_place_of_birth',
                  'next_of_kin_country','active','inactive_reason','living_status','patient_type',
                  'stage','created_at','last_updated_at','last_updated_overall_at','created_by',
                  'rdrf_registry', 'patientaddress_set', 'working_groups', 'consents')

    def resolve_sex(self, info):
        return dict(Patient.SEX_CHOICES).get(self.sex)

    def resolve_clinical_data(self, info, cde_keys=[]):
        clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection="cdes").all()

        context_form_ids = clinical_data.values_list("context_id", flat=True)
        context_lookup = {context.id: context for context in (RDRFContext.objects.filter(pk__in=list(context_form_ids)))}

        cfg_data_cnt_lookup = {context.context_form_group.id: 1 for context in RDRFContext.objects.filter(pk__in=list(context_form_ids))}

        values = []

        def add_value(cfg, form, section, section_cnt, cde, cde_keys):
            if 'code' in cde and mongo_key(form['name'], section['code'], cde['code']) in cde_keys:
                section_name = Section.objects.get(code=section['code']).display_name
                cde_name = CommonDataElement.objects.get(code=cde['code']).name
                values.append({'cfg': cfg,
                               'form': form['name'],
                               'section': {'code': section['code'], 'name': section_name, 'entry_num': section_cnt},
                               'cde': {'code': cde['code'], 'name': cde_name, 'value': cde['value']}})

        for idx, entry in enumerate(clinical_data):
            context = context_lookup[entry.context_id]
            cfg_id = context.context_form_group.id
            cfg_cnt = cfg_data_cnt_lookup[cfg_id]
            cfg_data_cnt_lookup[cfg_id] = (cfg_cnt + 1)
            cfg = {
                'name': context.context_form_group.name,
                'default_name': context.context_form_group.get_default_name(self, context),
                'sort_order': context.context_form_group.sort_order,
                'entry_num': cfg_cnt
            }
            if 'forms' in entry.data:
                for form in entry.data['forms']:
                    for section in form['sections']:
                        for idx, cde in enumerate(section['cdes']):
                            section_cnt = idx + 1 # 1-based index for output
                            if 'allow_multiple' in section and section['allow_multiple'] is True:
                                for cde_entry in cde:
                                    add_value(cfg, form, section, section_cnt, cde_entry, cde_keys)
                            else:
                                add_value(cfg, form, section, section_cnt, cde, cde_keys)

            values = sorted(values, key=lambda value: value['cfg']['sort_order'])

        # Create an empty clinical data value if patient has no clinical data for any required cde_keys
        # This is required particularly if none of the reported patients have entries for a cde
        for cde_key in cde_keys:
            form_name, section_code, cde_code = get_form_section_code(cde_key)
            form = RegistryForm.objects.get(name=form_name)
            section = Section.objects.get(code=section_code)
            cde = CommonDataElement.objects.get(code=cde_code)

            found = next((v for v in values if cde_key == mongo_key(v['form'], v['section']['code'], v['cde']['code'])), None)
            if not found:
                cfg = ContextFormGroup.objects.filter(items__registry_form=form).first()
                if cfg:
                    cfg_value = {'name': cfg.name, 'sort_order': cfg.sort_order, 'entry_num': 1}
                else:
                    cfg_value = {'name': 'Default', 'sort_order': 1, 'entry_num': 1}
                values.append({'cfg': cfg_value,
                               'form': form.name,
                               'section': {'code': section.code, 'name': section.display_name, 'entry_num': 1},
                               'cde': {'code': cde.code, 'name': cde.name, 'value': ''}})

        return values if values else [{}]

class ConsentQuestionType(DjangoObjectType):
    class Meta:
        model = ConsentQuestion
        fields = ('code', 'question_label')

class ConsentValueType(DjangoObjectType):
    class Meta:
        model = ConsentValue
        fields = ('consent_question', 'answer')

class NextOfKinRelationshipType(DjangoObjectType):
    class Meta:
        model = NextOfKinRelationship
        fields = ('relationship',)

class PatientAddressType(DjangoObjectType):
    class Meta:
        model = PatientAddress
        fields = ('id', 'address_type', 'address', 'suburb', 'country', 'state', 'postcode')

class AddressTypeType(DjangoObjectType):
    class Meta:
        model = AddressType
        fields = ('type',)

class WorkingGroupType(DjangoObjectType):
    display_name = graphene.String()
    class Meta:
        model = WorkingGroup
        fields = ('name',)

    def resolve_display_name(self, info):
        return self.display_name

class RegistryType(DjangoObjectType):
    class Meta:
        model = Registry
        fields = ('name', 'code')

class Query(graphene.ObjectType):
    debug = graphene.Field(DjangoDebug, name='_debug')
    all_patients = graphene.List(PatientType,
                                 registry_code=graphene.String(required=True),
                                 filters=graphene.List(graphene.String),
                                 working_group_ids=graphene.List(graphene.String))

    def resolve_all_patients(self, info, registry_code, filters=[], working_group_ids=[]):
        registry = Registry.objects.get(code=registry_code)

        query_args = dict([query_filter.split('=') for query_filter in filters])

        query_args['rdrf_registry__id'] = registry.id

        if working_group_ids:
            query_args['working_groups__id__in'] = working_group_ids

        return Patient.objects\
            .get_by_user_and_registry(info.context.user, registry)\
            .filter(**query_args).prefetch_related('working_groups')\
            .distinct()

schema = graphene.Schema(query=Query, types=[ClinicalDataCde, ClinicalDataCdeMultiValue])
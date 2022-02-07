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


class CdeInterface(graphene.Interface):
    code = graphene.String()
    name = graphene.String()
    abbreviated_name = graphene.String()

    @classmethod
    def resolve_type(self, instance, info):
        return CdeMultiValueType if type(instance['value']) is list else CdeValueType


class CdeValueType(graphene.ObjectType):
    class Meta:
        interfaces = (CdeInterface,)

    value = graphene.String()


class CdeMultiValueType(graphene.ObjectType):
    class Meta:
        interfaces = (CdeInterface,)

    values = graphene.List(graphene.String)

    def resolve_values(self, info):
        return self['value']


class SectionType(graphene.ObjectType):
    code = graphene.String()
    name = graphene.String()
    abbreviated_name = graphene.String()
    entry_num = graphene.String()


class RegistryFormType(graphene.ObjectType):
    name = graphene.String()
    nice_name = graphene.String()
    abbreviated_name = graphene.String()


class ContextFormGroupType(graphene.ObjectType):
    code = graphene.String()
    name = graphene.String()
    abbreviated_name = graphene.String()
    default_name = graphene.String()
    sort_order = graphene.String()
    entry_num = graphene.String()


class ClinicalDataType(graphene.ObjectType):
    cfg = graphene.Field(ContextFormGroupType)
    form = graphene.Field(RegistryFormType)
    section = graphene.Field(SectionType)
    cde = graphene.Field(CdeInterface)


class PatientType(DjangoObjectType):
    sex = graphene.String()
    clinical_data = graphene.List(ClinicalDataType, cde_keys=graphene.List(graphene.String))

    class Meta:
        model = Patient
        fields = ('id', 'consent', 'consent_clinical_trials', 'consent_sent_information',
                  'consent_provided_by_parent_guardian', 'family_name', 'given_names', 'maiden_name', 'umrn',
                  'date_of_birth', 'date_of_death', 'place_of_birth', 'date_of_migration', 'country_of_birth',
                  'ethnic_origin', 'sex', 'home_phone', 'mobile_phone', 'work_phone', 'email', 'next_of_kin_family_name',
                  'next_of_kin_given_names', 'next_of_kin_relationship', 'next_of_kin_address', 'next_of_kin_suburb',
                  'next_of_kin_state', 'next_of_kin_postcode', 'next_of_kin_home_phone', 'next_of_kin_mobile_phone',
                  'next_of_kin_work_phone', 'next_of_kin_email', 'next_of_kin_parent_place_of_birth',
                  'next_of_kin_country', 'active', 'inactive_reason', 'living_status', 'patient_type',
                  'stage', 'created_at', 'last_updated_at', 'last_updated_overall_at', 'created_by',
                  'rdrf_registry', 'patientaddress_set', 'working_groups', 'consents')

    def resolve_sex(self, info):
        return dict(Patient.SEX_CHOICES).get(self.sex, self.sex)

    def resolve_clinical_data(self, info, cde_keys=[]):
        clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection="cdes").order_by('created_at').all()

        context_form_ids = clinical_data.values_list("context_id", flat=True)
        context_lookup = {context.id: context for context in (RDRFContext.objects.filter(pk__in=list(context_form_ids)))}

        cfg_data_cnt_lookup = {context.context_form_group.id: 1 for context in RDRFContext.objects.filter(pk__in=list(context_form_ids))}

        values = []

        def add_value(cfg, form_model, section_model, section_cnt, cde_model, cde_value):
            values.append({'cfg': cfg,
                           'form': {'name': form_model.name, 'nice_name': form_model.nice_name, 'abbreviated_name': form_model.abbreviated_name},
                           'section': {'code': section_model.code, 'name': section_model.display_name, 'abbreviated_name': section_model.abbreviated_name, 'entry_num': section_cnt},
                           'cde': {'code': cde_model.code, 'name': cde_model.name, 'abbreviated_name': cde_model.abbreviated_name, 'value': cde_value}})

        def add_value_from_data_entry(cfg, form_model, section_model, section_cnt, cde_entry, cde_keys):
            if 'code' in cde_entry and mongo_key(form_model.name, section_model.code, cde_entry['code']) in cde_keys:
                cde_obj = CommonDataElement.objects.get(code=cde_entry['code'])
                add_value(cfg, form_model, section_model, section_cnt, cde_obj, cde_entry['value'])

        for idx, entry in enumerate(clinical_data):
            context = context_lookup[entry.context_id]
            cfg_id = context.context_form_group.id
            cfg_cnt = cfg_data_cnt_lookup[cfg_id]
            cfg_data_cnt_lookup[cfg_id] = (cfg_cnt + 1)
            cfg = {
                'code': context.context_form_group.code,
                'name': context.context_form_group.name,
                'default_name': context.context_form_group.get_default_name(self, context),
                'abbreviated_name': context.context_form_group.abbreviated_name,
                'sort_order': context.context_form_group.sort_order,
                'entry_num': cfg_cnt
            }
            if 'forms' in entry.data:
                for form in entry.data['forms']:
                    form_model = RegistryForm.objects.get(name=form['name'])
                    for section in form['sections']:
                        section_model = Section.objects.get(code=section['code'])
                        section_entry_num = 0
                        for cde in section['cdes']:
                            if 'allow_multiple' in section and section['allow_multiple'] is True:
                                section_entry_num = section_entry_num + 1
                                for cde_entry in cde:
                                    add_value_from_data_entry(cfg, form_model, section_model, section_entry_num, cde_entry, cde_keys)
                            else:
                                add_value_from_data_entry(cfg, form_model, section_model, 1, cde, cde_keys)
            values = sorted(values, key=lambda value: value['cfg']['sort_order'])

        # Create an empty clinical data value if patient has no clinical data for any required cde_keys
        # This is required particularly if none of the reported patients have entries for a cde
        for cde_key in cde_keys:
            form_name, section_code, cde_code = get_form_section_code(cde_key)
            form = RegistryForm.objects.get(name=form_name)
            section = Section.objects.get(code=section_code)
            cde = CommonDataElement.objects.get(code=cde_code)

            found = next((v for v in values if cde_key == mongo_key(v['form']['name'], v['section']['code'], v['cde']['code'])), None)
            if not found:
                cfg = ContextFormGroup.objects.filter(items__registry_form=form).first()

                if cfg:
                    cfg_value = {
                        'name': cfg.name,
                        'default_name': cfg.name,
                        'abbreviated_name': cfg.abbreviated_name,
                        'sort_order': cfg.sort_order,
                        'entry_num': 1
                    }
                else:
                    cfg_value = {'name': 'Default', 'abbreviated_name': 'Default', 'sort_order': 1, 'entry_num': 1}

                add_value(cfg_value, form, section, 1, cde, '')

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


schema = graphene.Schema(query=Query, types=[CdeValueType, CdeMultiValueType])

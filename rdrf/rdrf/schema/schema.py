import logging

import graphene
from graphene_django import DjangoObjectType
from graphene_django.debug import DjangoDebug

from rdrf.helpers.utils import mongo_key
from rdrf.models.definition.models import Registry, ConsentQuestion, ClinicalData, RDRFContext, ContextFormGroup
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient, PatientAddress, AddressType, ConsentValue, NextOfKinRelationship

logger = logging.getLogger(__name__)

class ClinicalDataCdeInterface(graphene.Interface):
    code = graphene.String()

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

class ContextFormGroupFlat(graphene.ObjectType):
    name = graphene.String()
    sort_order = graphene.String()
    entry_num = graphene.String()

class ClinicalDataTypeFlat(graphene.ObjectType):
    cfg = graphene.Field(ContextFormGroupFlat)
    form = graphene.String()
    section = graphene.String()
    section_cnt = graphene.String()
    cde = graphene.Field(ClinicalDataCdeInterface)
    # cde = graphene.String()
    # value = graphene.List(graphene.String)





class ClinicalDataSectionInterface(graphene.Interface):
    code = graphene.String()

    @classmethod
    def resolve_type(self, instance, info):
        return ClinicalDataMultiSection
        if 'allow_multiple' in instance and instance['allow_multiple'] is True:
            return ClinicalDataMultiSection
        else:
            return ClinicalDataSection

class ClinicalDataSection(graphene.ObjectType):
    class Meta:
        interfaces = (ClinicalDataSectionInterface,)

    cdes = graphene.List(ClinicalDataCdeInterface)

class ClinicalDataMultiSection(graphene.ObjectType):
    class Meta:
        interfaces = (ClinicalDataSectionInterface,)

    cdes_list = graphene.List(graphene.List(ClinicalDataCdeInterface))

    def resolve_cdes_list(self, info):
        return self['cdes']

class ClinicalDataForm(graphene.ObjectType):
    name = graphene.String()
    context_id = graphene.String()
    context_name = graphene.String()
    sections = graphene.List(ClinicalDataSectionInterface)
    timestamp = graphene.String()

class ContextFormGroupType(graphene.ObjectType):
    name = graphene.String()
    # entry_name =
    forms = graphene.List(ClinicalDataForm)

class ClinicalDataType(graphene.ObjectType):
    context_form_groups = graphene.List(ContextFormGroupType)


class PatientType(DjangoObjectType):
    clinical_data_flat = graphene.List(ClinicalDataTypeFlat, cde_keys=graphene.List(graphene.String))
    clinical_data = graphene.Field(ClinicalDataType, cde_keys=graphene.List(graphene.String))
    sex = graphene.String

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

    def resolve_clinical_data_flat(self, info, cde_keys=[]):
        clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection="cdes").all()

        if not clinical_data:
            return [{}]

        context_form_ids = clinical_data.values_list("context_id", flat=True)
        context_lookup = {context.id: context for context in (RDRFContext.objects.filter(pk__in=list(context_form_ids)))}

        cfg_data_cnt_lookup = {context.context_form_group.id: 1 for context in RDRFContext.objects.filter(pk__in=list(context_form_ids))}
        logger.info(cfg_data_cnt_lookup)

        values = []

        def add_value(cfg, form, section, section_cnt, cde, cde_keys):
            if 'code' in cde and mongo_key(form['name'], section['code'], cde['code']) in cde_keys:
                # cde_value = cde['value'] if type(cde['value']) is list else [(cde['value'])]
                values.append({'cfg': cfg, 'form': form['name'], 'section': section['code'], 'section_cnt': section_cnt, 'cde': {'code': cde['code'], 'value': cde['value']}})

        for idx, entry in enumerate(clinical_data):
            context = context_lookup[entry.context_id]
            cfg_id = context.context_form_group.id
            cfg_cnt = cfg_data_cnt_lookup[cfg_id]
            cfg_data_cnt_lookup[cfg_id] = (cfg_cnt + 1)
            cfg = {
                'name': context.context_form_group.name,
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
        return values

    def resolve_clinical_data(self, info, cde_keys=[]):

        def is_multisection(section):
            logger.info(section)
            return 'allow_multiple' in section and section['allow_multiple'] is True

        clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection="cdes")

        context_form_ids = clinical_data.values_list("context_id", flat=True)
        context_form_group_names = RDRFContext.objects.filter(pk__in=list(context_form_ids)).values("pk",
                                                                                                    "context_form_group__name")
        cfg_lookup = {cfg["pk"]: cfg["context_form_group__name"] for cfg in context_form_group_names}

        values = {}
        for datum in clinical_data:
            forms = []
            for form in datum.data['forms']:
                sections = []
                for section in form['sections']:
                    cdes = []
                    for cde in section['cdes']:
                        if is_multisection(section):
                            cdes_list = []
                            for c in cde:
                                if mongo_key(form['name'], section['code'], c['code']) in cde_keys:
                                    cdes_list.append(c)
                            if cdes_list: cdes.append(cdes_list)
                        else:
                            if mongo_key(form['name'], section['code'], cde['code']) in cde_keys:
                                cdes.append(cde)
                    if cdes: sections.append({'code': section['code'], 'allow_multiple': section['allow_multiple'], 'cdes': cdes})
                if sections: forms.append({'name': form['name'], 'timestamp': datum.data['timestamp'], 'sections': sections})
            if forms: values.setdefault(cfg_lookup[datum.context_id], []).extend(forms)

        return {"context_form_groups": [{"name": key, "forms": value} for key, value in values.items()]}


    # def resolve_clinical_data(self, info, cde_keys=[]):
    #
    #     def is_multisection(section):
    #         return 'allow_multiple' in section and section['allow_multiple'] is True
    #
    #     clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection="cdes")
    #
    #     context_form_ids = clinical_data.values_list("context_id", flat=True)
    #     rdrf_contexts = RDRFContext.objects.filter(pk__in=list(context_form_ids))
    #     cfg_object_lookup = {rc.id: rc.context_form_group for rc in rdrf_contexts}
    #     logger.info(rdrf_contexts)
    #     context_form_group_names = rdrf_contexts.values("pk","context_form_group__name")
    #     cfg_lookup = {cfg["pk"]: cfg["context_form_group__name"] for cfg in context_form_group_names}
    #
    #     values = {}
    #     for datum in clinical_data:
    #         rdrf_context = rdrf_contexts.get(id=datum.context_id)
    #         cfg = cfg_object_lookup[datum.context_id]
    #
    #         forms = []
    #         for form in datum.data['forms']:
    #             sections = []
    #             for section in form['sections']:
    #                 cdes = []
    #                 for cde in section['cdes']:
    #                     if is_multisection(section):
    #                         cdes_list = []
    #                         for c in cde:
    #                             if mongo_key(form['name'], section['code'], c['code']) in cde_keys:
    #                                 cdes_list.append(c)
    #                         if cdes_list: cdes.append(cdes_list)
    #                     else:
    #                         if mongo_key(form['name'], section['code'], cde['code']) in cde_keys:
    #                             cdes.append([cde])
    #                     # else:
    #                     #     if mongo_key(form['name'], section['code'], cde['code']) in cde_keys:
    #                     #         cdes.append(cde)
    #                 if cdes: sections.append({'code': section['code'], 'allow_multiple': section['allow_multiple'], 'cdes': cdes})
    #             if sections: forms.append({'name': form['name'], 'timestamp': datum.data['timestamp'], 'context_id': rdrf_context.id, 'context_name': cfg.get_default_name(self, rdrf_context), 'sections': sections})
    #         if forms: values.setdefault(cfg_lookup[datum.context_id], []).extend(forms)
    #
    #     return {"context_form_groups": [{"name": key, "forms": value} for key, value in values.items()]}

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
        fields = ('address_type', 'address', 'suburb', 'country', 'state', 'postcode')

class AddressTypeType(DjangoObjectType):
    class Meta:
        model = AddressType
        fields = ('type',)

class WorkingGroupType(DjangoObjectType):
    class Meta:
        model = WorkingGroup
        fields = ('id', 'name',)

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
            .filter(**query_args).prefetch_related('working_groups')\
            .distinct()

        # TODO uncomment before commit
        # return Patient.objects\
        #     .get_by_user_and_registry(info.context.user, registry)\
        #     .filter(**query_args).prefetch_related('working_groups')\
        #     .distinct()

schema = graphene.Schema(query=Query, types=[ClinicalDataMultiSection, ClinicalDataSection, ClinicalDataCde, ClinicalDataCdeMultiValue])

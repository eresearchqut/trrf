import graphene
import logging
import json
from graphene_django import DjangoObjectType
from graphene_django.debug import DjangoDebug

from rdrf.models.definition.models import Registry, ConsentQuestion, ClinicalData
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient, PatientAddress, AddressType, ConsentValue

logger = logging.getLogger(__name__)

class ClinicalDataType(graphene.ObjectType):
    form = graphene.String()
    section = graphene.String()
    cde = graphene.String()
    # TODO how to get around this limitation. Some values are just strings and some are lists,
    #  but how do I represent this with a typed field?
    value = graphene.List(graphene.String)


class PatientType(DjangoObjectType):
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
                  'next_of_kin_country','active','inactive_reason','user','carer','living_status','patient_type',
                  'stage','created_at','last_updated_at','last_updated_overall_at','created_by',
                  'rdrf_registry', 'patientaddress_set', 'working_groups', 'consents')


    def resolve_clinical_data(self, info, cde_keys=[]):
        clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection='cdes').first()
        values = []
        for form in clinical_data.data['forms']:
            for section in form['sections']:
                for cde in section['cdes']:
                    if 'code' in cde and f"{form['name']}_{section['code']}_{cde['code']}" in cde_keys:
                            cde_value = cde['value'] if type(cde['value']) is list else [(cde['value'])]
                            values.append(ClinicalDataType(form['name'], section['code'], cde['code'], cde_value))

        return values


class ConsentQuestionType(DjangoObjectType):
    class Meta:
        model = ConsentQuestion
        fields = ('code', 'question_label')

class ConsentValueType(DjangoObjectType):
    class Meta:
        model = ConsentValue
        fields = ('consent_question', 'answer')

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
                                 filters=graphene.List(graphene.String),
                                 working_group_ids=graphene.List(graphene.String))

    def resolve_all_patients(self, info, filters=[], working_group_ids=[]):
        query_args = dict([query_filter.split('=') for query_filter in filters])

        if working_group_ids:
            query_args['working_groups__id__in'] = working_group_ids


        # This works too: return Patient.objects.filter(id__in=Subquery(Patient.objects.filter(working_groups__id__in=[1,3]).values('id')))
        return Patient.objects.filter(**query_args).prefetch_related('working_groups').distinct()

schema = graphene.Schema(query=Query)
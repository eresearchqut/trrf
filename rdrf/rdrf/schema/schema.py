import graphene
import logging
from graphene_django import DjangoObjectType
from graphene_django.debug import DjangoDebug

from rdrf.models.definition.models import Registry, ConsentQuestion, ClinicalData
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient, PatientAddress, AddressType, ConsentValue

logger = logging.getLogger(__name__)

class ClinicalDataType(DjangoObjectType):
    class Meta:
        model = ClinicalData
        fields = ('data',)

class PatientType(DjangoObjectType):
    clinical_data = graphene.Field(ClinicalDataType)

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


    def resolve_clinical_data(self, info):
        clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection='cdes')
        logger.info(clinical_data)
        return clinical_data.first()


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

    # all_patients = graphene.List(PatientType,
    #                              registry_code=graphene.String(),
    #                              working_group_id=graphene.String(),
    #                              consents=graphene.List(graphene.String))

    # def resolve_all_patients(self, info, registry_code="", working_group_id="", consents=[]):

    def resolve_all_patients(self, info, filters=[], working_group_ids=[]):
        query_args = dict([query_filter.split('=') for query_filter in filters])

        if working_group_ids:
            query_args['working_groups__id__in'] = working_group_ids
            # This works too: Patient.objects.filter(id__in=Subquery(Patient.objects.filter(working_groups__id__in=[1,3]).values('id')))

        return Patient.objects.filter(**query_args).prefetch_related('working_groups').distinct()

schema = graphene.Schema(query=Query)
import graphene
import logging
from graphene_django import DjangoObjectType
from graphene_django.debug import DjangoDebug

from rdrf.helpers.utils import mongo_key
from rdrf.models.definition.models import Registry, ConsentQuestion, ClinicalData, RDRFContext
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient, PatientAddress, AddressType, ConsentValue

logger = logging.getLogger(__name__)

class ClinicalDataTypeFlat(graphene.ObjectType):
    form = graphene.String()
    section = graphene.String()
    cde = graphene.String()
    value = graphene.List(graphene.String)

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

class ClinicalDataSectionInterface(graphene.Interface):
    code = graphene.String()

    @classmethod
    def resolve_type(self, instance, info):
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
    sections = graphene.List(ClinicalDataSectionInterface)
    timestamp = graphene.String()

class ContextFormGroup(graphene.ObjectType):
    name = graphene.String()
    forms = graphene.List(ClinicalDataForm)

class ClinicalDataType(graphene.ObjectType):
    context_form_groups = graphene.List(ContextFormGroup)


class PatientType(DjangoObjectType):
    clinical_data_flat = graphene.List(ClinicalDataTypeFlat, cde_keys=graphene.List(graphene.String))
    clinical_data = graphene.Field(ClinicalDataType, cde_keys=graphene.List(graphene.String))

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

    def resolve_clinical_data_flat(self, info, cde_keys=[]):
        clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection="cdes").all()
        values = []

        def add_value(form, section, cde, cde_keys):
            # TODO replace with call to get_mongo_key
            if 'code' in cde and f"{form['name']}_{section['code']}_{cde['code']}" in cde_keys:
                cde_value = cde['value'] if type(cde['value']) is list else [(cde['value'])]
                values.append(ClinicalDataTypeFlat(form['name'], section['code'], cde['code'], cde_value))

        for entry in clinical_data:
            if 'forms' in entry.data:
                for form in entry.data['forms']:
                    for section in form['sections']:
                        for cde in section['cdes']:
                            if 'allow_multiple' in section and section['allow_multiple'] is True:
                                logger.info("this is a multi section")
                                logger.info(cde)
                                for cde_entry in cde:
                                    add_value(form, section, cde_entry, cde_keys)
                            else:
                                add_value(form, section, cde, cde_keys)
        return values

    # def resolve_clinical_data(self, info, cde_keys=[]):
    #
    #     # TODO only resolve clinical data with matching cde_keys
    #     clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection="cdes")
    #
    #     context_form_ids = clinical_data.values_list("context_id", flat=True)
    #     context_form_group_names = RDRFContext.objects.filter(pk__in=list(context_form_ids)).values("pk",
    #                                                                                                 "context_form_group__name")
    #     cfg_lookup = {cfg["pk"]: cfg["context_form_group__name"] for cfg in context_form_group_names}
    #
    #     values = {}
    #
    #     for clinical_datum in clinical_data:
    #         clinical_data_forms = [{
    #             "name": form["name"],
    #             "sections": form["sections"],
    #             "timestamp": clinical_datum.data["timestamp"]
    #         } for form in clinical_datum.data["forms"]]
    #
    #         values.setdefault(cfg_lookup[clinical_datum.context_id], []).extend(clinical_data_forms)
    #
    #     return {"context_form_groups": [{"name": key, "forms": value} for key, value in values.items()]}

    def resolve_clinical_data(self, info, cde_keys=[]):

        def is_multisection(section):
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

schema = graphene.Schema(query=Query, types=[ClinicalDataMultiSection, ClinicalDataSection, ClinicalDataCde, ClinicalDataCdeMultiValue])

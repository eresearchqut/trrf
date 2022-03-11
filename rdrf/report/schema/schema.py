import logging
import re

import graphene
from graphene_django import DjangoObjectType
from graphene_django.debug import DjangoDebug

from django.conf import settings
from django.utils.module_loading import import_string

from rdrf.forms.dsl.parse_utils import prefetch_form_data
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
        def add_value(cfg, form_model, section_model, section_cnt, cde_model, cde_value):
            values.append({'cfg': cfg,
                           'form': {'name': form_model.name, 'nice_name': form_model.nice_name, 'abbreviated_name': form_model.abbreviated_name},
                           'section': {'code': section_model.code, 'name': section_model.display_name, 'abbreviated_name': section_model.abbreviated_name, 'entry_num': section_cnt},
                           'cde': {'code': cde_model.code, 'name': cde_model.name, 'abbreviated_name': cde_model.abbreviated_name, 'value': cde_value}})

        def add_value_from_data_entry(cfg, form_model, section_model, section_cnt, cde_entry, cde_keys):
            if 'code' in cde_entry and mongo_key(form_model.name, section_model.code, cde_entry['code']) in cde_keys:
                cde_obj = CommonDataElement.objects.get(code=cde_entry['code'])
                add_value(cfg, form_model, section_model, section_cnt, cde_obj, cde_entry['value'])

        clinical_data = ClinicalData.objects.filter(django_id=self.id, django_model='Patient', collection="cdes").order_by('created_at').all()

        patient_contexts = RDRFContext.objects.filter(pk__in=list(clinical_data.values_list("context_id", flat=True)))

        context_lookup = {context.id: context for context in patient_contexts}
        cfg_counter_lookup = {context.context_form_group.id: 1 for context in patient_contexts}

        values = []

        for idx, entry in enumerate(clinical_data):
            context = context_lookup[entry.context_id]
            cfg = context.context_form_group
            cfg_dict = {
                'code': cfg.code,
                'name': cfg.name,
                'default_name': cfg.get_default_name(self, context),
                'abbreviated_name': cfg.abbreviated_name,
                'sort_order': cfg.sort_order,
                'entry_num': cfg_counter_lookup[cfg.id]
            }
            if 'forms' in entry.data:
                for form in entry.data['forms']:
                    form_model = RegistryForm.objects.get(name=form['name'])
                    for section in form['sections']:
                        section_model = Section.objects.get(code=section['code'])
                        section_entry_num = 0
                        for cde in section['cdes']:
                            if 'allow_multiple' in section and section['allow_multiple'] is True:
                                section_entry_num += 1
                                for cde_entry in cde:
                                    add_value_from_data_entry(cfg_dict, form_model, section_model, section_entry_num, cde_entry, cde_keys)
                            else:
                                add_value_from_data_entry(cfg_dict, form_model, section_model, 1, cde, cde_keys)
            values = sorted(values, key=lambda value: value['cfg']['sort_order'])
            cfg_counter_lookup[cfg.id] += 1

        # Create an empty clinical data value if patient has no clinical data for any required cde_keys
        # This is required particularly if none of the reported patients have entries for a cde
        for cde_key in cde_keys:
            form_name, section_code, cde_code = get_form_section_code(cde_key)
            form = RegistryForm.objects.get(name=form_name)
            section = Section.objects.get(code=section_code)
            cde = CommonDataElement.objects.get(code=cde_code)

            found = next((v for v in values if cde_key == mongo_key(v['form']['name'], v['section']['code'], v['cde']['code'])), None)
            if not found:
                cfg_dict = ContextFormGroup.objects.filter(items__registry_form=form).first()

                if cfg_dict:
                    cfg_value = {
                        'name': cfg_dict.name,
                        'default_name': cfg_dict.name,
                        'abbreviated_name': cfg_dict.abbreviated_name,
                        'sort_order': cfg_dict.sort_order,
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
    patient_type = import_string(settings.REPORT_PATIENT_CLASS)

    debug = graphene.Field(DjangoDebug, name='_debug')
    all_patients = graphene.List(patient_type,
                                 registry_code=graphene.String(required=True),
                                 consent_question_codes=graphene.List(graphene.String),
                                 working_group_ids=graphene.List(graphene.String),
                                 offset=graphene.Int(),
                                 limit=graphene.Int())

    def resolve_all_patients(self, info, registry_code, offset=None, limit=None, consent_question_codes=[], working_group_ids=[]):
        if limit and offset:
            limit += offset

        registry = Registry.objects.get(code=registry_code)

        query_args = dict()
        query_args['rdrf_registry__id'] = registry.id

        if working_group_ids:
            query_args['working_groups__id__in'] = working_group_ids

        if consent_question_codes:
            query_args['consents__answer'] = True
            query_args['consents__consent_question__code__in'] = consent_question_codes

        return Patient.objects\
            .get_by_user_and_registry(info.context.user, registry)\
            .filter(**query_args).prefetch_related('working_groups')\
            .distinct()[offset:limit]


schema = graphene.Schema(query=Query, types=[CdeValueType, CdeMultiValueType])


def list_patients(user, registry_code, consent_question_codes, working_group_ids):
    registry = Registry.objects.get(code=registry_code)
    query_args = dict()
    query_args['rdrf_registry__id'] = registry.id

    if working_group_ids:
        query_args['working_groups__id__in'] = working_group_ids

    if consent_question_codes:
        query_args['consents__answer'] = True
        query_args['consents__consent_question__code__in'] = consent_question_codes
    return Patient.objects \
        .get_by_user_and_registry(user, registry) \
        .filter(**query_args).prefetch_related('working_groups') \
        .distinct()


_graphql_field_pattern = re.compile("^[_a-zA-Z][_a-zA-Z0-9]*$")


def get_matching_name(s):
    if not _graphql_field_pattern.match(s):
        new_str = f"field_{s}"
        assert _graphql_field_pattern.match(new_str), f"Cannot use field '{s}' in graphql schema"
        return new_str
    return s


# TODO: memoize + possible cache clearing when registry definition changes?
def create_dynamic_schema():
    # TODO: rather than use bound-HOFs as resolvers:
    # Use only one resolver function for each level (cfg, form, section, cde), and
    # pass down reference to patient's entire clinical data through each resolver level, and
    # use resolver info parameters to retrieve scalar values from clinical data
    #
    # This will require less memory, but may be slower to fully resolve large queries

    def get_section_fields(_section_key, section_cdes):
        fields = {}
        for cde in section_cdes:
            field_name = get_matching_name(cde.code)

            if cde.allow_multiple:
                def multiple_cde_resolver(cdes, _info, cde_model=cde):
                    for cde_value in cdes:
                        if cde_value["code"] == cde_model.code:
                            return cde_value["value"]

                fields[field_name] = graphene.List(graphene.String)
                fields[f"resolve_{field_name}"] = multiple_cde_resolver
            else:
                def cde_resolver(cdes, _info, cde_model=cde):
                    for cde_value in cdes:
                        if cde_value["code"] == cde_model.code:
                            return cde_value["value"]

                fields[field_name] = graphene.String()
                fields[f"resolve_{field_name}"] = cde_resolver
        return fields

    def get_form_fields(form_key, section_models, section_cdes):
        fields = {}
        for section in section_models:
            section_key = f"{form_key}_{section.code}"
            section_type = type(
                f"DynamicSection_{section_key}",
                (graphene.ObjectType,),
                get_section_fields(section_key, section_cdes[section.code])
            )
            field_name = get_matching_name(section.code)

            def section_resolver(form_data, _info, section_model=section):
                for section_data in form_data["sections"]:
                    if section_data["code"] == section_model.code:
                        return section_data["cdes"]

            if section.allow_multiple:
                fields[field_name] = graphene.List(section_type)
            else:
                fields[field_name] = graphene.Field(section_type)
            fields[f"resolve_{field_name}"] = section_resolver
        return fields

    def get_cfg_forms(cfg_key, cfg_model):
        fields = {}

        form_models = cfg_model.forms

        if cfg_model.is_fixed:
            for form in form_models:
                section_models, section_cdes = prefetch_form_data(form)
                form_key = f"{cfg_key}_{form.name}"
                field_name = get_matching_name(form.name)

                def form_resolver(parent, _info, form_model=form):
                    _patient, _contexts, clinical_data = parent
                    assert len(clinical_data) <= 1, "Too many clinical data records to resolve form"

                    if len(clinical_data) == 0:
                        return None

                    for form_data in clinical_data[0].data["forms"]:
                        if form_data["name"] == form_model.name:
                            return form_data

                    return None

                fields[field_name] = graphene.Field(type(
                    f"DynamicForm_{form_key}",
                    (graphene.ObjectType,),
                    get_form_fields(form_key, section_models, section_cdes)
                ))
                fields[f"resolve_{field_name}"] = form_resolver
        else:
            form = form_models[0]
            section_models, section_cdes = prefetch_form_data(form)
            form_key = f"{cfg_key}_{form.name}"
            field_name = get_matching_name(form.name)

            def longitudinal_form_resolver(parent, _info, form_model=form):
                patient, contexts, clinical_data = parent
                form_data_list = list()

                context_lookup = {context.id: context for context in contexts}

                for clinical_datum in clinical_data:
                    for form_data in clinical_datum.data["forms"]:
                        if form_data["name"] == form_model.name:
                            context_model = context_lookup.get(clinical_datum.context_id)
                            assert context_model, "Unknown longitudinal context"

                            form_data_list.append({
                                "key": cfg_model.get_name_from_cde(patient, context_model),
                                "data": form_data
                            })

                return form_data_list

            fields[field_name] = graphene.List(type(
                f"DynamicForm_{form_key}",
                (graphene.ObjectType,),
                {
                    "key": graphene.String(),
                    "data": graphene.Field(type(
                        f"DynamicFormData_{form_key}",
                        (graphene.ObjectType,),
                        get_form_fields(form_key, section_models, section_cdes)
                    ))
                }
            ))
            fields[f"resolve_{field_name}"] = longitudinal_form_resolver

        return fields

    def get_clinical_data_fields():
        fields = {}
        for cfg in ContextFormGroup.objects.all():
            cfg_key = cfg.code
            field_name = get_matching_name(cfg.code)

            def cfg_resolver(parent, _info, cfg_model=cfg):
                patient, clinical_data = parent
                contexts = RDRFContext.objects.filter(object_id=patient.id, context_form_group=cfg_model.id)

                if not contexts:
                    return None

                # TODO: better query
                cfg_clinical_data = clinical_data.filter(context_id__in=[context.id for context in contexts])

                return patient, contexts, cfg_clinical_data

            fields[field_name] = graphene.Field(type(
                f"DynamicCFG_{cfg_key}",
                (graphene.ObjectType,),
                get_cfg_forms(cfg_key, cfg)
            ))
            fields[f"resolve_{field_name}"] = cfg_resolver
        return fields

    def clinical_data_resolver(patient, _info):
        return patient, ClinicalData.objects.filter(
            django_id=patient.id,
            django_model='Patient',
            collection="cdes"
        ).order_by('created_at').all()

    dynamic_patient = type("DynamicPatient", (DjangoObjectType,), {
        "Meta": type("Meta", (), {
            "model": Patient,
            "fields": ('id', 'consent', 'consent_clinical_trials', 'consent_sent_information',
                       'consent_provided_by_parent_guardian', 'family_name', 'given_names', 'maiden_name', 'umrn',
                       'date_of_birth', 'date_of_death', 'place_of_birth', 'date_of_migration', 'country_of_birth',
                       'ethnic_origin', 'sex', 'home_phone', 'mobile_phone', 'work_phone', 'email',
                       'next_of_kin_family_name',
                       'next_of_kin_given_names', 'next_of_kin_relationship', 'next_of_kin_address',
                       'next_of_kin_suburb',
                       'next_of_kin_state', 'next_of_kin_postcode', 'next_of_kin_home_phone',
                       'next_of_kin_mobile_phone',
                       'next_of_kin_work_phone', 'next_of_kin_email', 'next_of_kin_parent_place_of_birth',
                       'next_of_kin_country', 'active', 'inactive_reason', 'living_status', 'patient_type',
                       'stage', 'created_at', 'last_updated_at', 'last_updated_overall_at', 'created_by',
                       'rdrf_registry', 'patientaddress_set', 'working_groups', 'consents')
        }),
        "clinical_data": graphene.Field(type(
            "DynamicClinicalData",
            (graphene.ObjectType,),
            get_clinical_data_fields())
        ),
        "resolve_clinical_data": clinical_data_resolver,
        "test": graphene.String(),
        "resolve_test": lambda root, info: "Test value"
    })

    def resolve_patients(parent, _info, registry_code, offset=None, limit=None, consent_question_codes=[], working_group_ids=[]):
        if limit and offset:
            limit += offset

        return list_patients(_info.context.user, registry_code, consent_question_codes, working_group_ids)[offset:limit]

    dynamic_query = type("DynamicQuery", (graphene.ObjectType,), {
        "patients": graphene.List(dynamic_patient,
                                 registry_code=graphene.String(required=True),
                                 consent_question_codes=graphene.List(graphene.String),
                                 working_group_ids=graphene.List(graphene.String),
                                 offset=graphene.Int(),
                                 limit=graphene.Int()),
        "resolve_patients":  resolve_patients
    })



    return graphene.Schema(query=dynamic_query)

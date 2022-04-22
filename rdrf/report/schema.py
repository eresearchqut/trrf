import logging
import re
from functools import partial
from importlib import import_module

import graphene
from django.conf import settings
from django.db.models import Count, Max
from graphene_django import DjangoObjectType

from rdrf.forms.dsl.parse_utils import prefetch_form_data
from rdrf.forms.widgets.widgets import get_widget_class
from rdrf.models.definition.models import Registry, ClinicalData, RDRFContext, ContextFormGroup, ConsentQuestion
from registry.groups.models import WorkingGroup, CustomUser
from registry.patients.models import Patient, AddressType, PatientAddress, NextOfKinRelationship, ConsentValue, \
    PatientGUID

logger = logging.getLogger(__name__)

_graphql_field_pattern = re.compile("^[_a-zA-Z][_a-zA-Z0-9]*$")


class PatientGUIDType(DjangoObjectType):
    class Meta:
        model = PatientGUID
        fields = ('guid',)


class ConsentQuestionType(DjangoObjectType):
    class Meta:
        model = ConsentQuestion
        fields = ('code', 'question_label')


class ConsentValueType(DjangoObjectType):
    class Meta:
        model = ConsentValue
        fields = ('consent_question', 'answer', 'first_save', 'last_update')


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


class RegisteredClinician(DjangoObjectType):
    working_groups = graphene.String()

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'ethically_cleared')

    def resolve_working_groups(clinician, info):
        return ",".join([wg.display_name for wg in clinician.working_groups.all()])


class RegistryType(DjangoObjectType):
    class Meta:
        model = Registry
        fields = ('name', 'code')


def get_schema_field_name(s):
    if not _graphql_field_pattern.match(s):
        new_str = f"field{s}"
        assert _graphql_field_pattern.match(new_str), f"Cannot use field '{s}' in graphql schema"
        return new_str
    return s


def get_section_fields(_section_key, section_cdes):
    fields = {}
    for cde in section_cdes:
        field_name = get_schema_field_name(cde.code)

        def cde_resolver(cdes, _info, cde_model):
            for cde_value in cdes:
                if cde_value["code"] == cde_model.code:
                    datatype = cde_model.datatype.strip().lower()
                    value = cde_value["value"]
                    if datatype == 'lookup':
                        return get_widget_class(cde_model.widget_name).denormalized_value(value)
                    else:
                        return value

        if cde.allow_multiple:
            fields[field_name] = graphene.List(graphene.String, description=cde.name)
        else:
            fields[field_name] = graphene.String(description=cde.name)
        fields[f"resolve_{field_name}"] = partial(cde_resolver, cde_model=cde)

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
        field_name = get_schema_field_name(section.code)

        def section_resolver(form_data, _info, section_model):
            for section_data in form_data["sections"]:
                if section_data["code"] == section_model.code:
                    return section_data["cdes"]

        if section.allow_multiple:
            fields[field_name] = graphene.List(section_type, description=section.display_name)
        else:
            fields[field_name] = graphene.Field(section_type, description=section.display_name)
        fields[f"resolve_{field_name}"] = partial(section_resolver, section_model=section)
    return fields


def get_cfg_forms(cfg_key, cfg_model):
    fields = {}

    form_models = cfg_model.forms

    if cfg_model.is_fixed:
        for form in form_models:
            section_models, section_cdes = prefetch_form_data(form)
            form_key = f"{cfg_key}_{form.name}"
            field_name = get_schema_field_name(form.name)

            def form_resolver(parent, _info, form_model):
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
            ), description=form.name)
            fields[f"resolve_{field_name}"] = partial(form_resolver, form_model=form)
    else:
        assert len(form_models) == 1, "Too many forms for multiple context"
        form = form_models[0]
        section_models, section_cdes = prefetch_form_data(form)
        form_key = f"{cfg_key}_{form.name}"
        field_name = get_schema_field_name(form.name)

        def longitudinal_form_resolver(parent, _info, form_model):
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
                "key": graphene.String(description=cfg_model.naming_info),
                "data": graphene.Field(type(
                    f"DynamicFormData_{form_key}",
                    (graphene.ObjectType,),
                    get_form_fields(form_key, section_models, section_cdes)
                ), description=form.name)
            }
        ))
        fields[f"resolve_{field_name}"] = partial(longitudinal_form_resolver, form_model=form)

    return fields


def get_clinical_data_fields():
    fields = {}
    for cfg in ContextFormGroup.objects.all():
        cfg_key = cfg.code
        field_name = get_schema_field_name(cfg.code)

        def cfg_resolver(parent, _info, cfg_model):
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
        ), description=cfg.name)
        fields[f"resolve_{field_name}"] = partial(cfg_resolver, cfg_model=cfg)
    return fields


def get_patient_fields():
    return {
        "Meta": type("Meta", (), {
            "model": Patient,
            "fields": ['id', 'family_name', 'given_names', 'maiden_name', 'umrn',
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
                       'rdrf_registry', 'patientaddress_set', 'working_groups', 'registered_clinicians', 'consents',
                       'patientguid']
        }),
        "sex": graphene.String(),
        "resolve_sex": lambda patient, info: dict(Patient.SEX_CHOICES).get(patient.sex, patient.sex)
    }


def get_consent_fields():
    def consent_resolver(parent, _info, consent_question):
        patient, consents = parent
        return consents.filter(consent_question=consent_question).first()

    consent_fields = {}
    for consent_question in ConsentQuestion.objects.all():
        consent_fields[consent_question.code] = graphene.Field(ConsentValueType)
        consent_fields[f'resolve_{consent_question.code}'] = partial(consent_resolver, consent_question=consent_question)
    return consent_fields


def create_dynamic_patient_type():
    def consent_values_resolver(patient, _info):
        return patient, ConsentValue.objects.filter(
            patient=patient
        )

    def clinical_data_resolver(patient, _info):
        return patient, ClinicalData.objects.filter(
            django_id=patient.id,
            django_model='Patient',
            collection="cdes"
        ).order_by('created_at').all()

    schema_module = import_module(settings.SCHEMA_MODULE)
    patient_fields_func = getattr(schema_module, settings.SCHEMA_METHOD_PATIENT_FIELDS)
    patient_fields = patient_fields_func()

    consent_fields = get_consent_fields()

    if consent_fields:
        patient_fields.update({
            "consents": graphene.Field(type(
                "DynamicConsent",
                (graphene.ObjectType,),
                consent_fields),
            ),
            "resolve_consents": consent_values_resolver,
        })

    clinical_data_fields = get_clinical_data_fields()

    if clinical_data_fields:
        patient_fields.update({
            "clinical_data": graphene.Field(type(
                "DynamicClinicalData",
                (graphene.ObjectType,),
                get_clinical_data_fields()),
            ),
            "resolve_clinical_data": clinical_data_resolver,
        })

    return type("DynamicPatient", (DjangoObjectType,), patient_fields)


def create_dynamic_data_summary_type():
    data_summary_fields = {
        'max_address_count': graphene.Int(),
        'resolve_max_address_count': resolve_max_address_count,
        'max_working_group_count': graphene.Int(),
        'resolve_max_working_group_count': resolve_max_working_group_count,
        'max_clinician_count': graphene.Int(),
        'resolve_max_clinician_count': resolve_max_clinician_count,
        'list_consent_question_codes': graphene.List(graphene.String),
        'resolve_list_consent_question_codes': resolve_list_consent_question_codes
    }
    return type("DynamicDataSummary", (graphene.ObjectType,), data_summary_fields)


def list_patients_query(user,
                        registry_code,
                        consent_question_codes=None,
                        working_group_ids=None):
    registry = Registry.objects.get(code=registry_code)

    patient_query = Patient.objects \
        .get_by_user_and_registry(user, registry) \
        .prefetch_related('working_groups') \
        .prefetch_related('registered_clinicians')

    if working_group_ids:
        patient_query = patient_query.filter(working_groups__id__in=working_group_ids)

    if consent_question_codes:
        patient_query = patient_query.filter(
            consents__answer=True,
            consents__consent_question__code__in=consent_question_codes
        )

    return patient_query.distinct()


def list_patients_for_data_summary(user, data_summary):
    return list_patients_query(user, data_summary['registry_code'], data_summary['consent_question_codes'], data_summary['working_group_ids'])


def resolve_max_address_count(data_summary, info):
    return list_patients_for_data_summary(info.context.user, data_summary)\
        .annotate(Count('patientaddress'))\
        .aggregate(Max('patientaddress__count'))\
        .get('patientaddress__count__max') or 0


def resolve_max_working_group_count(data_summary, info):
    return list_patients_for_data_summary(info.context.user, data_summary)\
        .annotate(Count('working_groups'))\
        .aggregate(Max('working_groups__count'))\
        .get('working_groups__count__max')


def resolve_max_clinician_count(data_summary, info):
    return list_patients_for_data_summary(info.context.user, data_summary)\
        .annotate(Count('registered_clinicians'))\
        .aggregate(Max('registered_clinicians__count'))\
        .get('registered_clinicians__count__max')


def resolve_list_consent_question_codes(data_summary, info):
    return ConsentQuestion.objects.filter(section__registry__code=data_summary['registry_code']).order_by('position').values_list('code', flat=True)


# TODO: memoize + possible cache clearing when registry definition changes?
# TODO: Replace partial resolvers with single resolve function for each level
# TODO: Replace Metaprogramming with a low-level library like graphql-core
def create_dynamic_schema():
    if not Registry.objects.all().exists():
        return None
    dynamic_patient = create_dynamic_patient_type()
    dynamic_data_summary = create_dynamic_data_summary_type()

    def resolve_patients(_parent,
                         info,
                         registry_code,
                         offset=None,
                         limit=None,
                         consent_question_codes=None,
                         working_group_ids=None):
        if limit and offset:
            limit += offset

        return list_patients_query(info.context.user, registry_code, consent_question_codes, working_group_ids)[offset:limit]

    def resolve_data_summary(_parent, info, registry_code, consent_question_codes=None, working_group_ids=None):
        return {"registry_code": registry_code,
                "consent_question_codes": consent_question_codes,
                "working_group_ids": working_group_ids}

    dynamic_query = type("DynamicQuery", (graphene.ObjectType,), {
        "patients": graphene.List(dynamic_patient,
                                  registry_code=graphene.String(required=True),
                                  consent_question_codes=graphene.List(graphene.String),
                                  working_group_ids=graphene.List(graphene.String),
                                  offset=graphene.Int(),
                                  limit=graphene.Int()),
        "resolve_patients": resolve_patients,
        "data_summary": graphene.Field(dynamic_data_summary,
                                       registry_code=graphene.String(required=True),
                                       consent_question_codes=graphene.List(graphene.String),
                                       working_group_ids=graphene.List(graphene.String)),
        'resolve_data_summary': resolve_data_summary
    })

    return graphene.Schema(query=dynamic_query)

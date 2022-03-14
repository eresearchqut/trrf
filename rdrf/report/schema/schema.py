import logging
import re
from functools import partial

import graphene
from graphene_django import DjangoObjectType

from rdrf.forms.dsl.parse_utils import prefetch_form_data
from rdrf.models.definition.models import Registry, ClinicalData, RDRFContext, ContextFormGroup
from registry.patients.models import Patient

logger = logging.getLogger(__name__)

_graphql_field_pattern = re.compile("^[_a-zA-Z][_a-zA-Z0-9]*$")


def get_schema_field_name(s):
    if not _graphql_field_pattern.match(s):
        new_str = f"field_{s}"
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
                    return cde_value["value"]

        if cde.allow_multiple:
            fields[field_name] = graphene.List(graphene.String)
        else:
            fields[field_name] = graphene.String()
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
            fields[field_name] = graphene.List(section_type)
        else:
            fields[field_name] = graphene.Field(section_type)
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
            ))
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
                "key": graphene.String(),
                "data": graphene.Field(type(
                    f"DynamicFormData_{form_key}",
                    (graphene.ObjectType,),
                    get_form_fields(form_key, section_models, section_cdes)
                ))
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
        ))
        fields[f"resolve_{field_name}"] = partial(cfg_resolver, cfg_model=cfg)
    return fields


def create_dynamic_patient_type():
    def clinical_data_resolver(patient, _info):
        return patient, ClinicalData.objects.filter(
            django_id=patient.id,
            django_model='Patient',
            collection="cdes"
        ).order_by('created_at').all()

    clinical_data_fields = get_clinical_data_fields()

    patient_fields = {
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
        "sex": graphene.String(),
        "resolve_sex": lambda patient, info: dict(Patient.SEX_CHOICES).get(patient.sex, patient.sex)
    }

    if clinical_data_fields:
        patient_fields.update({
            "clinical_data": graphene.Field(type(
                "DynamicClinicalData",
                (graphene.ObjectType,),
                get_clinical_data_fields())
            ),
            "resolve_clinical_data": clinical_data_resolver,
        })

    return type("DynamicPatient", (DjangoObjectType,), patient_fields)


# TODO: memoize + possible cache clearing when registry definition changes?
# TODO: Replace partial resolvers with single resolve function for each level
# TODO: Replace Metaprogramming with a low-level library like graphql-core
def create_dynamic_schema():
    if not Registry.objects.all().exists():
        return None
    dynamic_patient = create_dynamic_patient_type()

    def resolve_patients(_parent,
                         info,
                         registry_code,
                         offset=None,
                         limit=None,
                         consent_question_codes=None,
                         working_group_ids=None):
        if limit and offset:
            limit += offset

        registry = Registry.objects.get(code=registry_code)

        patient_query = Patient.objects \
            .get_by_user_and_registry(info.context.user, registry) \
            .prefetch_related('working_groups')

        if working_group_ids:
            patient_query = patient_query.filter(working_groups__id__in=working_group_ids)

        if consent_question_codes:
            patient_query = patient_query.filter(
                consents__answer=True,
                consents__consent_question__code__in=consent_question_codes
            )

        return patient_query.distinct()[offset:limit]

    dynamic_query = type("DynamicQuery", (graphene.ObjectType,), {
        "patients": graphene.List(dynamic_patient,
                                  registry_code=graphene.String(required=True),
                                  consent_question_codes=graphene.List(graphene.String),
                                  working_group_ids=graphene.List(graphene.String),
                                  offset=graphene.Int(),
                                  limit=graphene.Int()),
        "resolve_patients": resolve_patients
    })

    return graphene.Schema(query=dynamic_query)

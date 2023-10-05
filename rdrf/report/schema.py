import logging
import re
from datetime import datetime
from functools import partial
from importlib import import_module

import graphene
from django.conf import settings
from django.contrib.postgres.lookups import Unaccent
from django.contrib.postgres.search import SearchVector
from django.db.models import Count, Max, Q, Value
from django.db.models.functions import Replace
from django.utils.translation import gettext as _
from graphene import ObjectType, InputObjectType
from graphene_django import DjangoObjectType

from rdrf.forms.dsl.parse_utils import prefetch_form_data
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry, ClinicalData, RDRFContext, ContextFormGroup, ConsentQuestion, \
    ConsentRule, EmailPreference
from registry.groups.models import WorkingGroup, CustomUser, WorkingGroupType
from registry.patients.models import Patient, AddressType, PatientAddress, NextOfKinRelationship, ConsentValue, \
    PatientGUID, ParentGuardian, LivingStates, PatientStage
from report.TrrfGraphQLView import PublicGraphQLError

logger = logging.getLogger(__name__)

_graphql_field_pattern = re.compile("^[_a-zA-Z][_a-zA-Z0-9]*$")

_valid_sort_fields = ['id', 'familyName', 'givenNames', 'dateOfBirth', 'sex', 'patientType', 'workingGroups.name',
                      'lastUpdatedOverallAt', 'stage.id', 'livingStatus']
_valid_search_fields = ['givenNames', 'familyName', 'stage']


def to_snake_case(name):
    from graphene.utils.str_converters import to_snake_case as to_snake_case_base
    snake_name = to_snake_case_base(name)

    return re.sub(r"\.", "__", snake_name)


def to_camel_case(name):
    from graphene.utils.str_converters import to_camel_case as to_camel_case_base
    camel_case_name = to_camel_case_base(name)  # Replace single underscores with camel cased name
    dot_case_name = re.sub(r"\_", ".", camel_case_name)  # Replace any remaining underscores with dots
    lower_dot_case_name = re.sub(r"\.([A-Z][a-z]*)?", lambda m: m.group(0).lower(), dot_case_name)  # Lower case the first letter following the dot
    return lower_dot_case_name


def validate_fields(fields, valid_fields, label):
    invalid_fields = list(set(fields).difference(valid_fields))
    if len(invalid_fields) > 0:
        raise PublicGraphQLError(
            _(f"Invalid {label}(s) provided: {', '.join(invalid_fields)}.\n "
              f"Valid values are: {', '.join(valid_fields)}."))


class QueryResult:
    def __init__(self, registry, all_patients):
        self.registry = registry
        self.all_patients = all_patients


class FacetValueType(ObjectType):
    label = graphene.String()
    value = graphene.String()
    total = graphene.Int()


class DataSummaryType(ObjectType):
    max_address_count = graphene.Int()
    max_working_group_count = graphene.Int()
    max_clinician_count = graphene.Int()
    max_parent_guardian_count = graphene.Int()
    list_consent_question_codes = graphene.List(graphene.List(graphene.String))

    def resolve_max_address_count(parent: QueryResult, _info):
        return parent.all_patients.annotate(Count('patientaddress')) \
                                  .aggregate(Max('patientaddress__count')) \
                                  .get('patientaddress__count__max') or 0

    def resolve_max_working_group_count(parent: QueryResult, _info):
        return parent.all_patients.annotate(Count('working_groups'))\
                                  .aggregate(Max('working_groups__count'))\
                                  .get('working_groups__count__max')

    def resolve_max_clinician_count(parent: QueryResult, _info):
        return parent.all_patients.annotate(Count('registered_clinicians'))\
                                  .aggregate(Max('registered_clinicians__count'))\
                                  .get('registered_clinicians__count__max')

    def resolve_max_parent_guardian_count(parent: QueryResult, _info):
        return parent.all_patients.annotate(Count('parentguardian'))\
                                  .aggregate(Max('parentguardian__count'))\
                                  .get('parentguardian__count__max') or 0

    def resolve_list_consent_question_codes(parent: QueryResult, _info):
        return ConsentQuestion.objects.filter(section__registry=parent.registry)\
                                      .order_by('position')\
                                      .values_list('section__code', 'code')


class PatientGUIDType(DjangoObjectType):
    class Meta:
        model = PatientGUID
        fields = ('guid',)


class ConsentQuestionType(DjangoObjectType):
    class Meta:
        model = ConsentQuestion
        fields = ('id', 'code', 'question_label')


class ConsentValueType(DjangoObjectType):
    class Meta:
        model = ConsentValue
        fields = ('consent_question', 'answer', 'first_save', 'last_update')


class NextOfKinRelationshipType(DjangoObjectType):
    class Meta:
        model = NextOfKinRelationship
        fields = ('relationship',)

    def resolve_relationship(next_of_kin_relationship, _info):
        return _(next_of_kin_relationship.relationship)


class PatientAddressType(DjangoObjectType):
    class Meta:
        model = PatientAddress
        fields = ('id', 'address_type', 'address', 'suburb', 'country', 'state', 'postcode')


class AddressTypeType(DjangoObjectType):
    class Meta:
        model = AddressType
        fields = ('type',)

    def resolve_type(address_type, _info):
        return _(address_type.type)


class WorkingGroupTypeType(DjangoObjectType):
    class Meta:
        model = WorkingGroupType
        fields = ('name',)


class WorkingGroupSchemaType(DjangoObjectType):
    display_name = graphene.String()

    class Meta:
        model = WorkingGroup
        fields = ('name', 'type')

    def resolve_display_name(self, _info):
        return self.display_name


class RegisteredClinician(DjangoObjectType):
    working_groups = graphene.String()

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'ethically_cleared')

    def resolve_working_groups(clinician, _info):
        return ",".join([wg.display_name for wg in clinician.working_groups.all()])


class RegistryType(DjangoObjectType):
    class Meta:
        model = Registry
        fields = ('name', 'code')


class ParentGuardianType(DjangoObjectType):
    email = graphene.String()
    self_patient_id = graphene.Int()
    gender = graphene.String()

    class Meta:
        model = ParentGuardian
        fields = ('first_name', 'last_name', 'date_of_birth', 'place_of_birth', 'date_of_migration', 'address',
                  'suburb', 'state', 'postcode', 'country', 'phone')

    def resolve_email(parent_guardian, _info):
        return parent_guardian.user.email if parent_guardian.user else None

    def resolve_self_patient_id(parent_guardian, _info):
        return parent_guardian.self_patient.id if parent_guardian.self_patient_id else None

    def resolve_gender(parent_guardian, _info):
        return dict(ParentGuardian.GENDER_CHOICES).get(parent_guardian.gender, parent_guardian.gender)


class EmailPreferencesType(ObjectType):
    unsubscribe_all = graphene.Boolean()

    def resolve_unsubscribe_all(email_preference, _info):
        return False if email_preference is None else email_preference.unsubscribe_all


class PatientStageType(DjangoObjectType):
    class Meta:
        model = PatientStage
        fields = ('id', 'name')


class FormMetaType(ObjectType):
    last_updated = graphene.DateTime(description="Timestamp this form was last updated")

    def resolve_last_updated(parent, _info):
        clinical_datum, form_name = parent
        timestamp_key = f'{form_name}_timestamp'
        if timestamp_key in clinical_datum.data:
            form_timestamp = clinical_datum.data[timestamp_key]
            return datetime.fromisoformat(form_timestamp)


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
                    return cde_model.display_value(cde_value["value"])

        if cde.allow_multiple:
            fields[field_name] = graphene.List(graphene.String, description=cde.name)
        else:
            fields[field_name] = graphene.String(description=cde.name)
        fields[f"resolve_{field_name}"] = partial(cde_resolver, cde_model=cde)

    return fields


def get_form_fields(form_key, section_models, section_cdes):
    fields = {'meta': graphene.Field(FormMetaType)}
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

                clinical_datum = clinical_data[0]
                for form_data in clinical_datum.data["forms"]:
                    if form_data["name"] == form_model.name:
                        form_data_dict = {'meta': (clinical_datum, form_model.name)}
                        form_data_dict.update(form_data)
                        return form_data_dict

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
                            "meta": (clinical_datum, form_model.name),
                            "data": form_data
                        })

            return form_data_list

        fields[field_name] = graphene.List(type(
            f"DynamicForm_{form_key}",
            (graphene.ObjectType,),
            {
                "key": graphene.String(description=cfg_model.naming_info),
                "meta": graphene.Field(FormMetaType),
                "data": graphene.Field(type(
                    f"DynamicFormData_{form_key}",
                    (graphene.ObjectType,),
                    get_form_fields(form_key, section_models, section_cdes)
                ), description=form.name)
            }
        ))
        fields[f"resolve_{field_name}"] = partial(longitudinal_form_resolver, form_model=form)

    return fields


def get_clinical_data_fields(registry):
    fields = {}
    for cfg in ContextFormGroup.objects.filter(registry=registry).all():
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

        forms = get_cfg_forms(cfg_key, cfg)

        # Drop any CFGs without forms.
        if forms:
            fields[field_name] = graphene.Field(type(
                f"DynamicCFG_{cfg_key}",
                (graphene.ObjectType,),
                forms
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
                       'next_of_kin_country', 'active', 'inactive_reason', 'patient_type',
                       'stage', 'created_at', 'last_updated_at', 'last_updated_overall_at', 'created_by',
                       'rdrf_registry', 'patientaddress_set', 'working_groups', 'registered_clinicians', 'consents',
                       'patientguid', 'parentguardian_set', 'stage']
        }),
        "sex": graphene.String(),
        "resolve_sex": lambda patient, _info: dict(Patient.SEX_CHOICES).get(patient.sex, patient.sex),
        "age": graphene.Int(),
        "resolve_age": lambda patient, _info: patient.age,
        "living_status": graphene.String(),
        "resolve_living_status": lambda patient, _info: dict(LivingStates.CHOICES).get(patient.living_status, patient.living_status)

    }


def get_consent_question_fields(consent_section):
    def consent_question_resolver(parent, _info, consent_question):
        patient, consents = parent
        return consents.filter(consent_question=consent_question).first()

    consent_fields = {}
    for consent_question in consent_section.questions.all():
        field_name = get_schema_field_name(consent_question.code)
        consent_fields[field_name] = graphene.Field(ConsentValueType)
        consent_fields[f'resolve_{field_name}'] = partial(consent_question_resolver, consent_question=consent_question)
    return consent_fields


def get_consent_section_fields(registry):
    def consent_section_resolver(parent, _info):
        return parent

    consent_fields = {}
    for consent_section in registry.consent_sections.all():
        field_name = get_schema_field_name(consent_section.code)
        consent_fields[field_name] = graphene.Field(type(f"DynamicConsentSection_{consent_section.registry.code}_{consent_section.code}",
                                                    (graphene.ObjectType,),
                                                    get_consent_question_fields(consent_section)))
        consent_fields[f'resolve_{field_name}'] = consent_section_resolver
    return consent_fields


def create_dynamic_facet_type(registry):
    def resolve_facet(parent, _info, facet_field, get_label_fn):
        results = parent.all_patients.values(facet_field).annotate(total=Count('id')).order_by()
        return [{'label': get_label_fn(item[facet_field]),
                 'value': item[facet_field],
                 'total': item['total']}
                for item in results]

    def get_living_status_label(status_id):
        living_states_dict = {choice_id: choice_label for choice_id, choice_label in LivingStates.CHOICES}
        return living_states_dict.get(status_id)

    def get_working_groups_name(wg_id):
        if wg_id:
            return WorkingGroup.objects.get(id=wg_id).name

    facet_fields = {}

    available_facets = [('living_status', get_living_status_label),
                        ('working_groups', get_working_groups_name)]

    for facet in available_facets:
        field, get_label = facet
        facet_fields[field] = graphene.List(FacetValueType)
        facet_fields[f'resolve_{field}'] = partial(resolve_facet, facet_field=field, get_label_fn=get_label)

    return type(f"DynamicFacet_{registry.code}", (ObjectType,), facet_fields)


def create_dynamic_patient_type(registry):
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

    def email_preferences_resolver(patient, _info):
        return EmailPreference.objects.get_by_user(patient.user)

    schema_module = import_module(settings.SCHEMA_MODULE)
    patient_fields_func = getattr(schema_module, settings.SCHEMA_METHOD_PATIENT_FIELDS)
    patient_fields = patient_fields_func()

    consent_fields = get_consent_section_fields(registry)

    if consent_fields:
        patient_fields.update({
            "consents": graphene.Field(type(
                f"DynamicConsent_{registry.code}",
                (graphene.ObjectType,),
                consent_fields),
            ),
            "resolve_consents": consent_values_resolver,
        })

    clinical_data_fields = get_clinical_data_fields(registry)

    if clinical_data_fields:
        patient_fields.update({
            "clinical_data": graphene.Field(type(
                f"DynamicClinicalData_{registry.code}",
                (graphene.ObjectType,),
                get_clinical_data_fields(registry)),
            ),
            "resolve_clinical_data": clinical_data_resolver,
        })

    patient_fields.update({
        "email_preferences": graphene.Field(EmailPreferencesType),
        "resolve_email_preferences": email_preferences_resolver,
    })

    return type(f"DynamicPatient_{registry.code}", (DjangoObjectType,), patient_fields)


def list_patients_query(user,
                        registry,
                        filter_args=None):

    patient_ids = Patient.objects.get_by_user_and_registry(user, registry).values('id')

    # Reload patient objects from filtered patients so that related objects aren't affected
    # For example, if a clinician was limited to certain working groups, but the patient was a member of additional working groups
    #              then we wouldn't be able to interact with those additional working groups later (e.g. filtering)
    patient_query = Patient.objects \
        .filter(id__in=patient_ids) \
        .prefetch_related('working_groups') \
        .prefetch_related('registered_clinicians')

    if filter_args.working_groups:
        null_wgs = [wg for wg in filter_args.working_groups if wg is None]
        filterable_wgs = [wg for wg in filter_args.working_groups if wg is not None]

        query_filterable_wgs = Q(working_groups__id__in=filterable_wgs)

        if null_wgs:
            query_working_groups = query_filterable_wgs | Q(working_groups__id__isnull=True)
        else:
            query_working_groups = query_filterable_wgs

        # Double negative intended here to ensure the working_groups that don't match the filter aren't excluded from the result set
        # We only want to exclude the *patients* that aren't in the working groups, not the working groups themselves
        patient_query = patient_query.exclude(~Q(query_working_groups))

    if filter_args.consent_questions:
        for id in filter_args.consent_questions:
            patient_query = patient_query.filter(consents__answer=True, consents__consent_question__id=id)

    if filter_args.living_status:
        patient_query = patient_query.filter(living_status__in=filter_args.living_status)

    if registry.has_feature(RegistryFeatures.CONSENT_CHECKS):
        consent_rules = ConsentRule.objects.filter(registry=registry, capability='see_patient', user_group__in=user.groups.all(), enabled=True)
        for consent_question in [consent_rule.consent_question for consent_rule in consent_rules]:
            patient_query = patient_query.filter(consents__answer=True, consents__consent_question=consent_question)

    return patient_query.distinct()


def create_dynamic_all_patients_type(registry):
    def resolve_facets(parent: QueryResult, _info):
        return parent

    def resolve_total(parent: QueryResult, _info):
        return parent.all_patients.count()

    def resolve_data_summary(parent: QueryResult, _info):
        return parent

    def resolve_patients(parent: QueryResult, _info, id=None, sort=None, offset=None, limit=None):
        def validate_sort_fields(sort_fields):
            sort_fields_without_order = [field.lstrip('-') for field in sort_fields]
            return validate_fields(sort_fields_without_order, _valid_sort_fields, 'sort field')

        all_patients = parent.all_patients

        if id:
            return all_patients.filter(id=id)

        if sort:
            validate_sort_fields(sort)
            sort_fields = [to_snake_case(field) for field in sort]
            all_patients = all_patients.order_by(*sort_fields)

        if limit and offset:
            limit += offset
        return all_patients[offset:limit]

    dynamic_query = type(f"DynamicAllPatients_{registry.code}", (graphene.ObjectType,), {
        'total': graphene.Int(),
        'resolve_total': resolve_total,
        'facets': graphene.Field(create_dynamic_facet_type(registry)),
        'resolve_facets': resolve_facets,
        'data_summary': graphene.Field(DataSummaryType),
        'resolve_data_summary': resolve_data_summary,
        'patients': graphene.List(create_dynamic_patient_type(registry),
                                  id=graphene.String(),
                                  sort=graphene.List(graphene.String),
                                  offset=graphene.Int(),
                                  limit=graphene.Int()),
        'resolve_patients': resolve_patients
    })

    return dynamic_query


class SearchType(InputObjectType):
    fields = graphene.List(graphene.String)
    text = graphene.String()


class PatientFilterType(InputObjectType):
    search = graphene.List(SearchType)
    working_groups = graphene.List(graphene.String)
    consent_questions = graphene.List(graphene.String)
    living_status = graphene.List(graphene.String)

    def __init__(self):
        self.search = []
        self.working_groups = []
        self.consent_questions = []
        self.living_status = []


def create_dynamic_registry_type(registry):

    def sanitise_search_field(field):
        return Unaccent(Replace(field, Value("'"), Value("")))

    def resolve_all_patients(registry,
                             _info,
                             filter_args=PatientFilterType()):

        all_patients = list_patients_query(_info.context.user, registry, filter_args)

        if filter_args.search:
            for i, search_def in enumerate(filter_args.search):
                search_text = sanitise_search_field(Value(search_def.text))

                validate_fields(search_def.fields, _valid_search_fields, 'search field')
                search_fields = [to_snake_case(field) for field in search_def.fields]

                search_annotations = {f'sanitised_{i}_{field}': sanitise_search_field(field) for field in search_fields}
                search_annotations.update({f'search_{i}': (SearchVector(*search_annotations.keys(), config='simple'))})

                all_patients = all_patients.annotate(**search_annotations).filter(**{f'search_{i}__icontains': search_text})

        return QueryResult(registry=registry,
                           all_patients=all_patients)

    dynamic_registry_fields = {
        'all_patients': graphene.Field(create_dynamic_all_patients_type(registry),
                                       filter_args=graphene.Argument(PatientFilterType)),
        'resolve_all_patients': resolve_all_patients,
    }
    return type(f'DynamicRegistryType_{registry.code}', (graphene.ObjectType,), dynamic_registry_fields)


# TODO: Replace partial resolvers with single resolve function for each level
# TODO: Replace Metaprogramming with a low-level library like graphql-core
def create_dynamic_schema():
    if not Registry.objects.all().exists():
        return None

    def resolve_registry(_parent, _info, registry):
        return registry

    dynamic_query_fields = {}

    for registry in Registry.objects.all():
        dynamic_query_fields.update({
            registry.code: graphene.Field(create_dynamic_registry_type(registry)),
            f"resolve_{registry.code}": partial(resolve_registry, registry=registry)
        })

    dynamic_query = type("DynamicQuery", (graphene.ObjectType,), dynamic_query_fields)

    return graphene.Schema(query=dynamic_query)

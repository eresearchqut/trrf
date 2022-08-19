from decimal import Decimal
import json
import logging
from operator import attrgetter
import yaml
from django.contrib.auth.models import Group

from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict

from rdrf import VERSION
import datetime
from rdrf.models.definition.models import DemographicFields, RegistryForm, RegistryDashboard
from rdrf.models.definition.models import Section, CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue
from registry.patients.models import PatientStage, PatientStageRule, NextOfKinRelationship

from explorer.models import Query
from report.models import ReportDesign

logger = logging.getLogger(__name__)


class ExportException(Exception):
    pass


def convert_decimal_values(cde_dict):
    for k in cde_dict:
        value = cde_dict[k]
        if isinstance(value, Decimal):
            cde_dict[k] = str(value)
    return cde_dict


def cde_to_dict(cde):
    return convert_decimal_values(model_to_dict(cde))


class ExportFormat:
    JSON = "JSON"
    YAML = "YAML"


class ExportType:
    # Only registry, forms , sections - No CDEs
    REGISTRY_ONLY = "REGISTRY_ONLY"
    # As above with cdes used by the registry
    REGISTRY_PLUS_CDES = "REGISTRY_PLUS_CDES"
    REGISTRY_PLUS_ALL_CDES = "REGISTRY_PLUS_ALL_CDES"   # registry + all cdes in the site
    # only the cdes in the supplied registry ( no forms)
    REGISTRY_CDES = "REGISTRY_CDES"
    ALL_CDES = "ALL_CDES"                               # All CDEs in the site


class Exporter:

    """
    Export a registry definition to yaml or json
    """

    def __init__(self, registry_model):
        self.registry = registry_model

    def _check_model_validity(self, model):
        try:
            model.clean()
        except ValidationError as verr:
            raise ExportException("Model validity exception for model {} !".format(model), verr)

    def _validate_section(self, section_code):
        try:
            section_model = Section.objects.get(code=section_code)
        except Section.DoesNotExist:
            raise
        self._check_model_validity(section_model)

    def validate(self, export_type):
        """"
        Validates the CDES, sections and registry forms
        Raises an ExporterException in case of error
        """
        cdes = self._get_cdes(export_type)
        for cde in cdes:
            self._check_model_validity(cde)
        if self.registry.patient_data_section:
            self._validate_section(self.registry.patient_data_section.code)

        for frm in RegistryForm.objects.filter(registry=self.registry).order_by("name"):
            if frm.name == self.registry.generated_questionnaire_name:
                # don't check the generated questionnaire
                continue
            self._check_model_validity(frm)
            for section_code in frm.get_sections():
                self._validate_section(section_code)

    def export_yaml(self, export_type=ExportType.REGISTRY_PLUS_CDES, validate=True):
        """
        Example output:
        ----------------------------------------------------------------------
        code: FH
        desc: This is a description that might take a few lines.
        forms:
        - is_questionnaire: false
          name: Foobar
          sections:
          - allow_multiple: false
            code: SEC001
            display_name: Physical Characteristics
            elements: [CDE01, CDE03, CDE05]
            extra: 0
          - allow_multiple: true
            code: SEC002
            display_name: Disease
            elements: [CDE88, CDE67]
            extra: 1
        - is_questionnaire: false
          name: Glug
          sections:
          - allow_multiple: false
            code: SEC89
            display_name: Test Section
            elements: [CDE99, CDE67]
            extra: 0
        name: FascioH.. Registry
        splash_screen: todo
        version: 1.0
        ----------------------------------------------------------------------


        :return: a yaml file containing the definition of a registry
        """
        try:
            if validate:
                self.validate(export_type)
            export = self._export(ExportFormat.YAML, export_type)
            return export, []
        except Exception as ex:
            logger.exception(ex)
            return None, [ex]

    def export_json(self, export_type=ExportType.REGISTRY_PLUS_CDES, validate=True):
        if validate:
            self.validate(export_type)
        return self._export(ExportFormat.JSON, export_type)

    def _get_cdes(self, export_type):
        if export_type == ExportType.REGISTRY_ONLY:
            cdes = set()
        elif export_type in [ExportType.REGISTRY_PLUS_CDES, ExportType.REGISTRY_CDES]:
            cdes = set(cde for cde in self._get_cdes_in_registry(self.registry))
        elif export_type in [ExportType.ALL_CDES, ExportType.REGISTRY_PLUS_ALL_CDES]:
            cdes = set(cde for cde in CommonDataElement.objects.order_by("code"))
        else:
            raise ExportException("Unknown export type")

        generic_cdes = self._get_generic_cdes()
        return self._sort_codes(cdes.union(generic_cdes))

    @staticmethod
    def _sort_codes(items):
        return sorted(items, key=attrgetter("code"))

    def _get_pvgs_in_registry(self, registry):
        pvgs = set()

        for cde in self._get_cdes_in_registry(registry):
            if cde.pv_group:
                pvgs.add(cde.pv_group)
        return pvgs

    def _get_pvgs(self, export_type):
        if export_type == ExportType.REGISTRY_ONLY:
            pvgs = set()
        elif export_type in [ExportType.REGISTRY_PLUS_CDES, ExportType.REGISTRY_CDES]:
            pvgs = set(pvg for pvg in self._get_pvgs_in_registry(self.registry))
        elif export_type in [ExportType.ALL_CDES, ExportType.REGISTRY_PLUS_ALL_CDES]:
            pvgs = set(pvg for pvg in CDEPermittedValueGroup.objects.order_by("code"))
        else:
            raise ExportException("Unknown export type")
        return self._sort_codes(pvgs)

    def _get_registry_version(self):
        return self.registry.version.strip()

    def _create_section_map(self, section_code, optional=False):
        try:
            section_model = Section.objects.get(code=section_code)
        except Section.DoesNotExist:
            if optional:
                return {}
            raise
        section_map = {}
        section_map["display_name"] = section_model.display_name
        section_map["questionnaire_display_name"] = section_model.questionnaire_display_name
        section_map["code"] = section_model.code
        section_map["abbreviated_name"] = section_model.abbreviated_name
        section_map["extra"] = section_model.extra
        section_map["allow_multiple"] = section_model.allow_multiple
        section_map["elements"] = section_model.get_elements()
        section_map["questionnaire_help"] = section_model.questionnaire_help
        return section_map

    def _create_form_map(self, form_model):
        frm_map = {}
        frm_map["name"] = form_model.name
        frm_map["abbreviated_name"] = form_model.abbreviated_name
        frm_map["header"] = form_model.header
        frm_map["display_name"] = form_model.display_name
        frm_map["questionnaire_display_name"] = form_model.questionnaire_display_name
        frm_map["is_questionnaire"] = form_model.is_questionnaire
        frm_map["questionnaire_questions"] = form_model.questionnaire_questions
        frm_map["position"] = form_model.position
        frm_map["sections"] = []
        frm_map["applicability_condition"] = form_model.applicability_condition
        frm_map["conditional_rendering_rules"] = form_model.conditional_rendering_rules or ''
        frm_map["tags"] = form_model.tags

        for section_code in form_model.get_sections():
            frm_map["sections"].append(self._create_section_map(section_code))

        return frm_map

    def _get_forms_allowed_groups(self):
        d = {}

        for form in self.registry.forms:
            d[form.name] = [g.name for g in form.groups_allowed.order_by("name")]
        return d

    def _get_forms_readonly_groups(self):
        return {form.name: [group.name for group in form.groups_readonly.order_by("name")] for form in self.registry.forms}

    def _export(self, format, export_type):
        data = {}
        data["RDRF_VERSION"] = VERSION
        data["EXPORT_TYPE"] = export_type
        data["EXPORT_TIME"] = str(datetime.datetime.now())
        data["cdes"] = [cde_to_dict(cde) for cde in self._get_cdes(export_type)]
        data["pvgs"] = [pvg.as_dict for pvg in self._get_pvgs(export_type)]
        data["REGISTRY_VERSION"] = self._get_registry_version()
        data["metadata_json"] = self.registry.metadata_json
        data["consent_sections"] = self._get_consent_sections()
        data["consent_configuration"] = self._get_consent_configuration()
        data["forms_allowed_groups"] = self._get_forms_allowed_groups()
        data["forms_readonly_groups"] = self._get_forms_readonly_groups()
        data["demographic_fields"] = self._get_demographic_fields()
        data["complete_fields"] = self._get_complete_fields()
        data["reports"] = self._get_reports()
        data["reports_v2"] = self._get_reports_v2()
        data["cde_policies"] = self._get_cde_policies()
        data["context_form_groups"] = self._get_context_form_groups()
        data["email_notifications"] = self._get_email_notifications()
        data["consent_rules"] = self._get_consent_rules()
        data["form_titles"] = self._get_form_titles()

        if self.registry.patient_data_section:
            data["patient_data_section"] = self._create_section_map(
                self.registry.patient_data_section.code)
        else:
            data["patient_data_section"] = {}

        data["working_groups"] = self._get_working_groups()
        data["patient_stages"] = self._get_patient_stages()
        data["patient_stage_rules"] = self._get_patient_stage_rules()
        data["next_of_kin_relationships"] = self._get_next_of_kin_relationships()
        data["group_permissions"] = self._get_group_permissions()
        data["registry_dashboards"] = self.get_registry_dashboards()

        if export_type in [
                ExportType.REGISTRY_ONLY,
                ExportType.REGISTRY_PLUS_ALL_CDES,
                ExportType.REGISTRY_PLUS_CDES]:
            data["name"] = self.registry.name
            data["code"] = self.registry.code
            data["desc"] = self.registry.desc
            data["splash_screen"] = self.registry.splash_screen
            data["forms"] = []
            generic_sections = [
                self._create_section_map(section_code, optional=True)
                for section_code in
                self.registry.generic_sections]
            data["generic_sections"] = [gs for gs in generic_sections if gs]

            for frm in RegistryForm.objects.filter(registry=self.registry).order_by("name"):
                if frm.name == self.registry.generated_questionnaire_name:
                    # don't export the generated questionnaire
                    continue
                data["forms"].append(self._create_form_map(frm))

        if format == ExportFormat.YAML:
            try:
                export_data = dump_yaml(data)
            except Exception:
                logger.exception("Error yaml dumping")
                export_data = None
        elif format == ExportFormat.JSON:
            export_data = json.dumps(data)
        elif format is None:
            export_data = data
        else:
            raise Exception("Unknown format: %s" % format)

        return export_data

    def export_cdes_yaml(self, all_cdes=False):
        """
        Export common data element definitions

        :param all_cdes: if True export all CDEs in the database. If False(default)
        Then export only the CDEs used by the self.registry
        :return: return YAML file of all CDEs
        """
        return self._export_cdes(all_cdes, ExportFormat.YAML)

    def _export_cdes(self, all_cdes):
        if all_cdes:
            cdes = CommonDataElement.objects.order_by("code")
        else:
            cdes = self._get_cdes_in_registry(self.registry)

        data = {}

        if all_cdes:
            data["registry"] = "*"
        else:
            data["registry"] = self.registry.code

        data["cdes"] = []
        data["value_groups"] = []

        groups_used = set()

        for cde_model in cdes:
            cde_map = {}
            cde_map["code"] = cde_model.code
            cde_map["name"] = cde_model.name
            cde_map["desc"] = cde_model.desc
            cde_map["datatype"] = cde_model.datatype
            cde_map["instructions"] = cde_model.instructions

            if cde_model.pv_group:
                cde_map["pv_group"] = cde_model.pv_group.code
                groups_used.add(cde_model.pv_group.code)
            else:
                cde_map["pv_group"] = ""

            cde_map["allow_multiple"] = cde_model.allow_multiple
            cde_map["max_length"] = cde_model.max_length
            cde_map["min_value"] = str(cde_model.min_value)
            cde_map["max_value"] = str(cde_model.max_value)
            cde_map["is_required"] = cde_model.is_required
            cde_map["important"] = cde_model.important
            cde_map["pattern"] = cde_model.pattern
            cde_map["widget_name"] = cde_model.widget_name
            cde_map["calculation"] = cde_model.calculation
            cde_map["questionnaire_text"] = cde_model.questionnaire_text

            data["cdes"].append(cde_map)

        for group_code in groups_used:
            group_map = {}

            pvg = CDEPermittedValueGroup.objects.get(code=group_code)
            group_map["code"] = pvg.code
            group_map["values"] = []
            for value in CDEPermittedValue.objects.filter(
                    pv_group=pvg).order_by("position", "code"):
                value_map = {}
                value_map["code"] = value.code
                value_map["value"] = value.value
                value_map["questionnaire_value"] = value.questionnaire_value
                value_map["desc"] = value.desc
                value_map["position"] = value.position

                group_map["values"].append(value_map)

            data["value_groups"].append(group_map)

        if format == ExportFormat.YAML:
            export_cde__data = dump_yaml(data)
        elif format == ExportFormat.JSON:
            export_cde__data = json.dumps(data)
        else:
            raise Exception("Unknown format: %s" % format)

        return export_cde__data

    def _get_cdes_in_registry(self, registry_model):
        cdes = set()
        for registry_form in RegistryForm.objects.filter(registry=registry_model):
            section_codes = registry_form.get_sections()
            cdes = cdes.union(self._get_cdes_for_sections(section_codes))

        if registry_model.patient_data_section:
            patient_data_section_cdes = set(registry_model.patient_data_section.cde_models)
        else:
            patient_data_section_cdes = set()

        cdes = cdes.union(patient_data_section_cdes)

        generic_cdes = self._get_generic_cdes()
        cdes = cdes.union(generic_cdes)

        return self._sort_codes(cdes)

    def _get_consent_configuration(self):
        consent_config = getattr(self.registry, "consent_configuration", None)
        if consent_config:
            return {
                "consent_locked": consent_config.consent_locked,
                "esignature": consent_config.esignature,
            }

    def _get_consent_sections(self):
        section_dicts = []
        for consent_section in self.registry.consent_sections.order_by("code"):
            section_dict = {"code": consent_section.code,
                            "section_label": consent_section.section_label,
                            "information_link": consent_section.information_link,
                            "information_text": consent_section.information_text,
                            "applicability_condition": consent_section.applicability_condition,
                            "validation_rule": consent_section.validation_rule,
                            "questions": []}
            for consent_model in consent_section.questions.order_by("position", "code"):
                cm = {"code": consent_model.code,
                      "position": consent_model.position,
                      "question_label": consent_model.question_label,
                      "questionnaire_label": consent_model.questionnaire_label,
                      "instructions": consent_model.instructions}
                section_dict["questions"].append(cm)
            section_dicts.append(section_dict)

        return section_dicts

    def _get_cdes_for_sections(self, section_codes, sections_optional=False):
        cdes = set()
        for section_code in section_codes:
            try:
                section_model = Section.objects.get(code=section_code)
                section_cde_codes = section_model.get_elements()
                for cde_code in section_cde_codes:
                    try:
                        cde = CommonDataElement.objects.get(code=cde_code)
                        cdes.add(cde)
                    except CommonDataElement.DoesNotExist as dne:
                        logger.error("No CDE with code: %s" % cde_code)
                        raise ExportException(f"Section {section_code} referes to CDE {cde_code} that does not exist", dne)

            except Section.DoesNotExist as sne:
                if not sections_optional:
                    logger.error("No Section with code: %s" % section_code)
                    raise ExportException(f"Section does not exist: {section_code}", sne)
        return cdes

    def _get_generic_cdes(self):
        return self._get_cdes_for_sections(self.registry.generic_sections, sections_optional=True)

    def _get_working_groups(self):
        from registry.groups.models import WorkingGroup
        return [wg.name for wg in WorkingGroup.objects.filter(registry=self.registry)]

    def _get_demographic_fields(self):
        demographic_fields = []

        for demographic_field in DemographicFields.objects.filter(registry=self.registry):
            fields = {}
            fields['registry'] = demographic_field.registry.code
            fields['groups'] = [g.name for g in demographic_field.groups.all()]
            fields['field'] = demographic_field.field
            fields['status'] = demographic_field.status
            fields['is_section'] = demographic_field.is_section
            demographic_fields.append(fields)

        return demographic_fields

    def _get_complete_fields(self):
        forms = RegistryForm.objects.filter(registry=self.registry)
        complete_fields = []

        for form in forms:
            if form.complete_form_cdes.exists():
                form_cdes = {}
                form_cdes["form_name"] = form.name
                form_cdes["cdes"] = [
                    cde.code for cde in form.complete_form_cdes.order_by("code")]
                complete_fields.append(form_cdes)

        return complete_fields

    def _get_reports(self):
        registry_queries = Query.objects.filter(registry=self.registry)

        queries = []
        for query in registry_queries:
            q = {}
            q["registry"] = query.registry.code
            q["access_group"] = [ag.name for ag in query.access_group.order_by("name")]
            q["title"] = query.title
            q["description"] = query.description
            q["mongo_search_type"] = query.mongo_search_type
            q["sql_query"] = query.sql_query
            q["collection"] = query.collection
            q["criteria"] = query.criteria
            q["projection"] = query.projection
            q["aggregation"] = query.aggregation
            q["created_by"] = query.created_by
            q["created_at"] = query.created_at
            queries.append(q)

        return queries

    def _get_reports_v2(self):
        return [{'title': r.title,
                 'description': r.description,
                 'registry': r.registry.code,
                 'access_groups': [ag.name for ag in r.access_groups.all()],
                 'filter_working_groups': [wg.name for wg in r.filter_working_groups.all()],
                 'filter_consents': [{'section': c.section.code, 'code': c.code} for c in r.filter_consents.all()],
                 'clinical_data_fields': [{'cde_key': f.cde_key, 'context_form_group': f.context_form_group.code} for f in r.reportclinicaldatafield_set.all()],
                 'demographic_fields': [{'model': f.model, 'field': f.field, 'sort_order': f.sort_order} for f in r.reportdemographicfield_set.all()]
                 }
                for r in (ReportDesign.objects.filter(registry=self.registry)
                                              .select_related('registry')
                                              .prefetch_related('access_groups',
                                                                'filter_working_groups',
                                                                'filter_consents',
                                                                'reportclinicaldatafield_set',
                                                                'reportdemographicfield_set'))]

    def _get_cde_policies(self):
        from rdrf.models.definition.models import CdePolicy
        cde_policies = []
        for cde_policy in CdePolicy.objects.filter(
                registry=self.registry).order_by("cde__code"):
            cde_pol_dict = {}
            cde_pol_dict["cde_code"] = cde_policy.cde.code
            cde_pol_dict["groups_allowed"] = [
                group.name for group in cde_policy.groups_allowed.order_by("name")]
            cde_pol_dict["condition"] = cde_policy.condition
            cde_policies.append(cde_pol_dict)
        return cde_policies

    def _get_context_form_groups(self):
        from rdrf.models.definition.models import ContextFormGroup
        data = []
        for cfg in ContextFormGroup.objects.filter(registry=self.registry).order_by("name"):
            cfg_dict = {}
            cfg_dict["context_type"] = cfg.context_type
            cfg_dict["code"] = cfg.code
            cfg_dict["name"] = cfg.name
            cfg_dict["abbreviated_name"] = cfg.abbreviated_name
            cfg_dict["naming_scheme"] = cfg.naming_scheme
            cfg_dict["is_default"] = cfg.is_default
            cfg_dict["naming_cde_to_use"] = cfg.naming_cde_to_use
            cfg_dict["sort_order"] = cfg.sort_order
            cfg_dict["forms"] = []
            for form in cfg.forms:
                cfg_dict["forms"].append(form.name)
            cfg_dict["ordering"] = cfg.ordering
            data.append(cfg_dict)
        return data

    def _get_email_notifications(self):
        from rdrf.models.definition.models import EmailNotification
        data = []

        def get_template_dict(t):
            return {"language": t.language,
                    "description": t.description,
                    "subject": t.subject,
                    "body": t.body}

        for email_notification in EmailNotification.objects.filter(
                registry=self.registry).order_by("description"):
            en_dict = {}
            en_dict["description"] = email_notification.description
            en_dict["email_from"] = email_notification.email_from
            en_dict["recipient"] = email_notification.recipient
            if email_notification.group_recipient:
                en_dict["group_recipient"] = email_notification.group_recipient.name
            else:
                en_dict["group_recipient"] = None
            en_dict["email_templates"] = [get_template_dict(t) for t in
                                          email_notification.email_templates.all()]

            en_dict["disabled"] = email_notification.disabled
            data.append(en_dict)
        return data

    def _get_consent_rules(self):
        from rdrf.models.definition.models import ConsentRule
        data = []
        for consent_rule in ConsentRule.objects.filter(registry=self.registry):
            consent_rule_dict = {}
            consent_rule_dict["user_group"] = consent_rule.user_group.name
            consent_rule_dict["capability"] = consent_rule.capability
            consent_rule_dict["consent_section_code"] = consent_rule.consent_question.section.code
            consent_rule_dict["consent_question_code"] = consent_rule.consent_question.code
            consent_rule_dict["enabled"] = consent_rule.enabled
            data.append(consent_rule_dict)
        return data

    def _get_form_titles(self):
        from rdrf.models.definition.models import FormTitle
        data = []
        for form_title in FormTitle.objects.filter(registry=self.registry):
            title_dict = {}
            title_dict["default_title"] = form_title.default_title
            title_dict["custom_title"] = form_title.custom_title
            title_dict["order"] = form_title.order
            title_dict["groups"] = [
                g.name for g in form_title.groups.all()
            ]
            data.append(title_dict)

    def _get_patient_stages(self):
        data = []
        for stage in PatientStage.objects.filter(registry=self.registry):
            stage_dict = {
                "id": stage.id,
                "name": stage.name,
                "next_stages": [next_stage.id for next_stage in stage.allowed_next_stages.all()],
                "prev_stages": [prev_stage.id for prev_stage in stage.allowed_prev_stages.all()],
            }
            data.append(stage_dict)
        return data

    def _get_patient_stage_rules(self):
        data = []
        for rule in PatientStageRule.objects.filter(registry=self.registry):
            from_stage = rule.from_stage.id if rule.from_stage else None
            to_stage = rule.to_stage.id if rule.to_stage else None
            rule_dict = {
                "id": rule.id,
                "condition": rule.condition,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "order": rule.order,
            }
            data.append(rule_dict)
        return data

    def _get_next_of_kin_relationships(self):
        return list(NextOfKinRelationship.objects.all().values_list("relationship", flat=True))

    def _get_group_permissions(self):
        data = []
        for group in Group.objects.all():
            permissions = []
            for permission in group.permissions.all():
                permission_dict = {
                    "name": permission.name,
                    "codename": permission.codename,
                    "content_type": permission.content_type.natural_key()
                }
                permissions.append(permission_dict)
            group_dict = {
                "name": group.name,
                "permissions": permissions
            }
            data.append(group_dict)
        return data

    def get_registry_dashboards(self):
        return [{
                'registry': dashboard.registry.code,
                'widgets': [{'widget_type': widget.widget_type,
                             'title': widget.title,
                             'free_text': widget.free_text,
                             'demographics': [{'sort_order': demographic.sort_order,
                                               'label': demographic.label,
                                               'model': demographic.model,
                                               'field': demographic.field}
                                              for demographic in widget.demographics.all()],
                             'cdes': [{'sort_order': cde.sort_order,
                                       'label': cde.label,
                                       'context_form_group': cde.context_form_group.code,
                                       'registry_form': cde.registry_form.name,
                                       'section': cde.section.code,
                                       'cde': cde.cde.code}
                                      for cde in widget.cdes.all()],
                            'links': [{'sort_order': link.sort_order,
                                       'label': link.label,
                                       'context_form_group': link.context_form_group.code,
                                       'registry_form': link.registry_form.name} for link in widget.links.all()]}
                            for widget in dashboard.widgets.all()]
                } for dashboard in RegistryDashboard.objects.all()]


def str_presenter(dumper, data):
    lines = data.splitlines()
    if len(lines) > 1:
        # strip trailing whitespace on lines -- it's not significant,
        # and otherwise the dumper will use the quoted and escaped
        # string style.
        data = "\n".join(map(str.rstrip, lines))
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="|")
    else:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)


class ExportDumper(yaml.SafeDumper):
    pass


ExportDumper.add_representer(str, str_presenter)


def dump_yaml(data):
    return yaml.dump(data, Dumper=ExportDumper, allow_unicode=True,
                     default_flow_style=False)

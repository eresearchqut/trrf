import logging
from collections import OrderedDict

from aws_xray_sdk.core import xray_recorder

from rdrf.helpers.utils import mongo_key
from rdrf.models.definition.models import ClinicalData, RDRFContext, ContextFormGroup, RegistryForm, Section, \
    CommonDataElement
from report.models import ReportCdeHeadingFormat
from report.schema.schema import list_patients_query

logger = logging.getLogger(__name__)

class ClinicalDataReportUtil:

    def __init__(self):
        self.report_cdes = []

    def __context_lookup(self, context_id):
        return RDRFContext.objects.get(pk=context_id)

    def __extract_cde_data(self, form_name, section_code, processed_cdes, allow_multiple, cdes):
        if allow_multiple:
            for cde_entry in cdes:
                return self.__extract_cde_data(form_name, section_code, processed_cdes, False, cde_entry)
        cdes_data = {}
        for cde in cdes:
            cde_code = cde['code']
            if mongo_key(form_name, section_code, cde_code) in self.report_cdes:
                cde_value = cde['value']
                processed_cde = processed_cdes.get(cde_code, {})
                cnt_cde_values = len(cde_value) if type(cde_value) is list else 1
                cdes_data.setdefault(cde_code, {
                    'count': max(processed_cde.get('count', 1), cnt_cde_values)
                })
        return cdes_data

    def __extract_section_data(self, form_name, processed_sections, sections):
        sections_data = {}
        for section in sections:
            section_code = section['code']
            section_cdes = section['cdes']
            processed_cdes = processed_sections.get(section_code, {}).get('cdes', {})

            cdes_data = self.__extract_cde_data(form_name,
                                                section_code,
                                                processed_cdes,
                                                section.get('allow_multiple', False),
                                                section_cdes)

            if cdes_data:
                sections_data.setdefault(section_code, {
                    'count': max(len(section_cdes), processed_cdes.get('count', 1)),
                    'cdes': cdes_data
                })
        return sections_data

    def __extract_forms_data(self, processed_forms, forms):
        forms_data = {}
        for form in forms:
            form_name = form['name']
            processed_sections = processed_forms.get(form_name, {})

            sections_data = self.__extract_section_data(form_name, processed_sections, form['sections'])
            if sections_data:
                forms_data.setdefault(form_name, sections_data)
        return forms_data

    def __cde_heading(self, cde, heading_format):
        if heading_format == ReportCdeHeadingFormat.ABBR_NAME.value:
            return cde.abbreviated_name
        if heading_format == ReportCdeHeadingFormat.LABEL.value:
            return cde.name
        if heading_format == ReportCdeHeadingFormat.CODE.value:
            return cde.code

    def __section_heading(self, section, heading_format):
        if heading_format == ReportCdeHeadingFormat.ABBR_NAME.value:
            return section.abbreviated_name
        if heading_format == ReportCdeHeadingFormat.LABEL.value:
            return section.display_name
        if heading_format == ReportCdeHeadingFormat.CODE.value:
            return section.code

    def __form_heading(self, form, heading_format):
        if heading_format == ReportCdeHeadingFormat.ABBR_NAME.value:
            return form.abbreviated_name
        if heading_format == ReportCdeHeadingFormat.LABEL.value:
            return form.nice_name
        if heading_format == ReportCdeHeadingFormat.CODE.value:
            return form.name

    def __cfg_heading(self, cfg, heading_format):
        if heading_format == ReportCdeHeadingFormat.ABBR_NAME.value:
            return cfg.abbreviated_name
        if heading_format == ReportCdeHeadingFormat.LABEL.value:
            return cfg.name
        if heading_format == ReportCdeHeadingFormat.CODE.value:
            return cfg.code

    def __form_header_parts(self, cfg, cfg_heading, cfg_i, form, form_label_text):
        if cfg.is_fixed:
            form_key_suffix = form.name
            form_label_suffix = form_label_text
        else:
            form_key_suffix = f'{form.name}_{cfg_i}'
            form_label_suffix = f'{form_label_text}_{(cfg_i + 1)}'

        key_prefix = f'clinicalData_{cfg.code}_{form_key_suffix}'
        label = f'{cfg_heading}_{form_label_suffix}'
        return key_prefix, label

    def __cde_header_parts(self, form_key_prefix, form_key_suffix, form_label_prefix, section, section_heading, section_num, cde, cde_heading):
        if section.allow_multiple:
            section_key = f'{section.code}_{section_num}'
            section_label = f'{section_heading}_{(section_num + 1)}'
        else:
            section_key = section.code
            section_label = section_heading
        key = f'{form_key_prefix}{form_key_suffix}_{section_key}_{cde.code}'
        label = f'{form_label_prefix}_{section_label}_{cde_heading}'
        return key, label

    def csv_headers(self, user, report_design):
        xray_recorder.begin_subsegment('csv_headers')

        xray_recorder.begin_subsegment('list_patients')
        patients = list_patients_query(user,
                                       report_design.registry.code,
                                       [cq.code for cq in report_design.filter_consents.all()],
                                       [wg.id for wg in report_design.filter_working_groups.all()])
        xray_recorder.end_subsegment()

        xray_recorder.begin_subsegment('load all clinical data')
        all_clinical_data = ClinicalData.objects.filter(django_id__in=(list(patients.values_list("id", flat=True))),
                                                        django_model='Patient',
                                                        collection="cdes").all()
        xray_recorder.end_subsegment()

        self.report_cdes = report_design.reportclinicaldatafield_set.values_list('cde_key', flat=True)

        report_items = {}
        cfg_contexts_counter = {}

        # Step 1 - Summarise all clinical data
        xray_recorder.begin_subsegment('summarise clinical data')
        for entry in all_clinical_data:
            context = self.__context_lookup(entry.context_id)
            cfg = context.context_form_group

            cfg_data = report_items.get(cfg.code, {})
            forms_data = self.__extract_forms_data(cfg_data.get('forms', {}), entry.data['forms'])

            if forms_data:
                cfg_data = {'forms': forms_data}
                report_items[cfg.code] = cfg_data

            # Keep count of number of longitudinal entries by patient
            # e.g. {'cfg-1': {'patientA': 1, 'patientB': 3}}
            cfg_contexts_counter.setdefault(cfg.code, {}).setdefault(context.object_id, 0)
            cfg_contexts_counter[cfg.code][context.object_id] += 1
        xray_recorder.end_subsegment()

        # Step 2 - Generate headers from report summary
        xray_recorder.begin_subsegment('generate headers from summary')
        headers = OrderedDict()

        for cfg_code, cfg_data in report_items.items():
            max_cfg_count = max(val for key, val in cfg_contexts_counter[cfg_code].items())
            cfg = ContextFormGroup.objects.get(code=cfg_code)
            cfg_heading = self.__cfg_heading(cfg, report_design.cde_heading_format)
            for form_name, form_data in cfg_data['forms'].items():
                form = RegistryForm.objects.get(name=form_name)
                form_heading = self.__form_heading(form, report_design.cde_heading_format)
                for cfg_i in range(max_cfg_count):
                    form_key_prefix, form_label_prefix = self.__form_header_parts(cfg, cfg_heading, cfg_i, form, form_heading)
                    if cfg.is_multiple:
                        headers[f'{form_key_prefix}_key'] = f'{form_label_prefix}_Name'
                        form_key_suffix = '_data'
                    else:
                        form_key_suffix = ''
                    for section_code, section_data in form_data.items():
                        section = Section.objects.get(code=section_code)
                        section_heading = self.__section_heading(section, report_design.cde_heading_format)
                        for section_i in range(section_data['count']):
                            for cde_code, cde_data in section_data['cdes'].items():
                                cde = CommonDataElement.objects.get(code=cde_code)
                                cde_heading = self.__cde_heading(cde, report_design.cde_heading_format)
                                cde_key, cde_label = self.__cde_header_parts(form_key_prefix, form_key_suffix, form_label_prefix, section, section_heading, section_i, cde, cde_heading)
                                if cde_data['count'] == 1:
                                    headers[cde_key] = cde_label
                                else:
                                    for cde_i in range(cde_data['count']):
                                        headers.update({f"{cde_key}_{cde_i}": f"{cde_label}_{cde_i+1}"})
        xray_recorder.end_subsegment()
        xray_recorder.end_subsegment()
        return headers

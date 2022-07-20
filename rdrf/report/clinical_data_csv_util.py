import itertools
import logging
from collections import OrderedDict

from django.db import connections
from django.db.models import Count

from django.conf import settings
from rdrf.helpers.utils import get_form_section_code
from rdrf.models.definition.models import RDRFContext, ContextFormGroup, RegistryForm, Section, \
    CommonDataElement
from report.models import ReportCdeHeadingFormat
from report.schema import list_patients_query, get_schema_field_name, PatientFilterType

logger = logging.getLogger(__name__)


class ClinicalDataCsvUtil:

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
        form_name_key = get_schema_field_name(form.name)
        if cfg.is_fixed:
            form_key_suffix = form_name_key
            form_label_suffix = form_label_text
        else:
            form_key_suffix = f'{form_name_key}_{cfg_i}'
            form_label_suffix = f'{form_label_text}_{(cfg_i + 1)}'

        key_prefix = f'clinicalData_{cfg.code}_{form_key_suffix}'
        label = f'{cfg_heading}_{form_label_suffix}'
        return key_prefix, label

    def __cde_header_parts(self, form_key_prefix, form_key_suffix, form_label_prefix, section, section_heading, section_num, cde, cde_heading):
        section_code_key = get_schema_field_name(section.code)
        if section.allow_multiple:
            section_key = f'{section_code_key}_{section_num}'
            section_label = f'{section_heading}_{(section_num + 1)}'
        else:
            section_key = section_code_key
            section_label = section_heading
        key = f'{form_key_prefix}{form_key_suffix}_{section_key}_{get_schema_field_name(cde.code)}'
        label = f'{form_label_prefix}_{section_label}_{cde_heading}'
        return key, label

    def __clinical_data_summary(self, patient_ids, cde_keys):
        sql = """
            WITH cd_sections AS (
                     SELECT id, form_name, jsonb_extract_path_text(cd_forms.sections, 'code') section_code, jsonb_array_elements(cd_forms.sections#>'{cdes}') cdes
                     FROM (
                        SELECT id, jsonb_extract_path_text(cd.form, 'name') form_name, jsonb_array_elements(cd.form#>'{sections}') sections
                        FROM (SELECT id, jsonb_array_elements(data#>'{forms}') as form
                              FROM rdrf_clinicaldata
                              WHERE django_model = 'Patient'
                              AND   collection = 'cdes'
                              AND   django_id = ANY(%(patient_ids)s)
                              ) AS cd
                     ) as cd_forms
               ), sections_summary AS (
                     SELECT form_name, section_code, max(cnt_sections) max_cnt_sections
                     FROM (
                        SELECT id, form_name, section_code, count(section_code) cnt_sections
                        FROM cd_sections
                        WHERE jsonb_typeof(cdes) = 'array'
                        GROUP BY id, form_name, section_code
                        UNION
                        SELECT id, form_name, section_code, 1 cnt_sections
                        FROM cd_sections
                        WHERE jsonb_typeof(cdes) = 'object'
                        GROUP BY id, form_name, section_code
                     ) as cd_grp_cnt_section
                     GROUP BY form_name, section_code
               ), cde_summary AS (
                     SELECT form_name, section_code, cde_code, max(cde_value_cnt) max_cnt_cde_values
                     FROM (
                           SELECT id, form_name, section_code, cde_code, cde_value,
                                  case jsonb_typeof(cde_value)
                                    when 'array' then  jsonb_array_length(cde_value)
                                    else 1
                                  end cde_value_cnt
                           FROM (
                                 SELECT id, form_name, section_code, jsonb_extract_path_text(cdes, 'code') cde_code, jsonb_extract_path(cdes, 'value') cde_value
                                 FROM cd_sections
                                 WHERE jsonb_typeof(cdes) = 'object'
                                 UNION
                                 SELECT id, form_name, section_code, jsonb_extract_path_text(mcdes.multi_cde, 'code') cde_code, jsonb_extract_path(mcdes.multi_cde, 'value') cde_value
                                 FROM (
                                    SELECT id, form_name, section_code, jsonb_array_elements(cdes) multi_cde
                                    FROM cd_sections
                                    WHERE jsonb_typeof(cdes) = 'array') as mcdes
                                 ) as cde_data
                           ) as cde_entries
                     GROUP BY form_name, section_code, cde_code
               )
            SELECT ss.form_name, ss.section_code, ss.max_cnt_sections, cs.cde_code, cs.max_cnt_cde_values
            FROM   sections_summary ss
            JOIN   cde_summary cs
            on     cs.form_name = ss.form_name
            AND    cs.section_code = ss.section_code
            AND    concat(cs.form_name, (%(cde_delim)s), cs.section_code, (%(cde_delim)s), cs.cde_code) = ANY(%(cde_keys)s)
            ORDER BY cs.form_name, cs.section_code, cs.cde_code;
        """

        with connections['clinical'].cursor() as cursor:
            cursor.execute(sql, {'patient_ids': patient_ids, 'cde_delim': settings.FORM_SECTION_DELIMITER, 'cde_keys': cde_keys})
            rows = cursor.fetchall()

            summary = {
                form_name: {
                    section_code: {
                        'count': section_count,
                        'cdes': {row[3]: {'count': row[4]}
                                 for row in cdes}}
                    for (section_code, section_count), cdes in itertools.groupby(sections, lambda x: (x[1], x[2]))
                }
                for form_name, sections in itertools.groupby(rows, lambda x: x[0])
            }

        # Fill in the blanks with defaults
        for form_name, section_code, cde_code in map(get_form_section_code, cde_keys):
            # Check if any combination of this form, section, cde is not in the existing summary
            if not (form_name in summary and section_code in summary[form_name] and cde_code in summary[form_name][section_code]['cdes']):
                # Add defaults for for the data where it does not exist
                section_data = summary.setdefault(form_name, {}).setdefault(section_code, {'count': 1, 'cdes': {}})
                section_data['cdes'][cde_code] = {'count': 1}

        return summary

    def _form_section_cde_sort_order(self, cde_keys):
        sort_order_lookup = {}  # {formkey: {order: 1, sections: {sectionkey: {order: 1, cdes: {cdekey: 1}}}}

        for cde_i, cde_key in enumerate(cde_keys):
            form_name, section_code, cde_code = get_form_section_code(cde_key)

            sort_order_lookup.setdefault(form_name, {'order': len(sort_order_lookup), 'sections': {}})
            section_lookup = sort_order_lookup[form_name].get('sections')
            section_lookup.setdefault(section_code, {'order': len(section_lookup), 'cdes': {}})
            cde_lookup = sort_order_lookup[form_name]['sections'][section_code].get('cdes')
            cde_lookup.setdefault(cde_code, len(cde_lookup))

        return sort_order_lookup

    def __sorted_forms(self, unsorted_forms_dict, sort_order_lookup):
        return dict(sorted(unsorted_forms_dict.items(), key=lambda item: sort_order_lookup[item[0]]['order'])).items()

    def __sorted_sections(self, unsorted_sections_dict, sort_order_lookup, form_name):
        return dict(sorted(unsorted_sections_dict.items(), key=lambda item: sort_order_lookup[form_name]['sections'][item[0]]['order'])).items()

    def __sorted_cdes(self, unsorted_cdes_dict, sort_order_lookup, form_name, section_code):
        return dict(sorted(unsorted_cdes_dict.items(), key=lambda item: sort_order_lookup[form_name]['sections'][section_code]['cdes'][item[0]])).items()

    def __get_max_count_cfg_entries(self, cfg):
        # Get counts of entries per patient (object_id) for this context form group
        # Take the first count in the result set, which works out to be the max count of number of patient entries
        max_cnt_entries = \
            RDRFContext.objects.filter(context_form_group=cfg) \
                               .values('context_form_group', 'object_id') \
                               .annotate(cnt_entries=Count('object_id')) \
                               .order_by('-cnt_entries')[:1]

        return max_cnt_entries.first()['cnt_entries'] if max_cnt_entries else 1

    def __get_cfg_data(self, cfg, cfgs_lookup, heading_format):
        cfg_lookup = cfgs_lookup.get(cfg.code, None)
        if not cfg_lookup:
            cfg_lookup = {'count': self.__get_max_count_cfg_entries(cfg),
                          'header': self.__cfg_heading(cfg, heading_format)}
            cfgs_lookup[cfg.code] = cfg_lookup

        return cfg_lookup["header"], cfg_lookup['count']

    def __get_report_cfgs(self, report_design):
        report_cfg_ids = report_design.reportclinicaldatafield_set.distinct('context_form_group').values('context_form_group')
        return ContextFormGroup.objects.filter(id__in=report_cfg_ids)

    def csv_headers(self, user, report_design):
        cde_keys = list(report_design.reportclinicaldatafield_set.order_by('id').values_list('cde_key', flat=True))

        # Step 1 - Summarise all clinical data
        patient_filters = PatientFilterType()
        patient_filters.working_groups = [wg.id for wg in report_design.filter_working_groups.all()]
        patient_filters.consent_questions = [cq.id for cq in report_design.filter_consents.all()]

        patient_ids = list(list_patients_query(user,
                                               report_design.registry,
                                               patient_filters).values_list("id", flat=True))
        cd_summary = self.__clinical_data_summary(patient_ids, cde_keys)

        # Step 2 - Generate headers from summary
        cfgs_lookup = {}  # e.g. {'cfgcode': {'count': 1, 'heading': 'formatted heading'}}
        sort_order_lookup = self._form_section_cde_sort_order(cde_keys)
        report_cfgs = self.__get_report_cfgs(report_design)

        headers = OrderedDict()

        for form_name, form_data in self.__sorted_forms(cd_summary, sort_order_lookup):
            form = RegistryForm.objects.get(name=form_name)
            form_heading = self.__form_heading(form, report_design.cde_heading_format)
            for cfg in report_cfgs.filter(items__registry_form=form):
                cfg_heading, longitudinal_entries_cnt = self.__get_cfg_data(cfg, cfgs_lookup, report_design.cde_heading_format)

                for cfg_i in range(longitudinal_entries_cnt):
                    form_key_prefix, form_label_prefix = self.__form_header_parts(cfg, cfg_heading, cfg_i, form, form_heading)
                    if cfg.is_multiple:
                        headers[f'{form_key_prefix}_key'] = f'{form_label_prefix}_Name'
                        form_key_suffix = '_data'
                    else:
                        form_key_suffix = ''

                    for section_code, section_data in self.__sorted_sections(form_data, sort_order_lookup, form_name):
                        section = Section.objects.get(code=section_code)
                        section_heading = self.__section_heading(section, report_design.cde_heading_format)
                        for section_i in range(section_data['count']):

                            for cde_code, cde_data in self.__sorted_cdes(section_data['cdes'], sort_order_lookup, form_name, section_code):

                                cde = CommonDataElement.objects.get(code=cde_code)
                                cde_heading = self.__cde_heading(cde, report_design.cde_heading_format)
                                cde_key, cde_label = self.__cde_header_parts(form_key_prefix, form_key_suffix,
                                                                             form_label_prefix, section,
                                                                             section_heading, section_i, cde,
                                                                             cde_heading)

                                if cde_data['count'] > 1 or cde.allow_multiple:
                                    for cde_i in range(cde_data['count']):
                                        headers.update({f"{cde_key}_{cde_i}": f"{cde_label}_{cde_i + 1}"})
                                else:
                                    headers[cde_key] = cde_label
        return headers

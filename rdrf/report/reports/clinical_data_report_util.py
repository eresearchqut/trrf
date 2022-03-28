import logging
from collections import OrderedDict

from django.db import connections
from django.db.models import Count

from rdrf import settings
from rdrf.helpers.utils import mongo_key, get_form_section_code
from rdrf.models.definition.models import RDRFContext, ContextFormGroup, RegistryForm, Section, \
    CommonDataElement
from report.models import ReportCdeHeadingFormat

logger = logging.getLogger(__name__)


class ClinicalDataReportUtil:

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

    def __clinical_data_summary(self, cde_keys):
        sql = """
            WITH cd_sections AS (
                     SELECT id, form_name, jsonb_extract_path_text(cd_forms.sections, 'code') section_code, jsonb_array_elements(cd_forms.sections#>'{cdes}') cdes
                     FROM (
                        SELECT id, jsonb_extract_path_text(cd.form, 'name') form_name, jsonb_array_elements(cd.form#>'{sections}') sections
                        FROM (SELECT id, jsonb_array_elements(data#>'{forms}') as form
                              FROM rdrf_clinicaldata
                              WHERE django_model = 'Patient'
                              AND   collection = 'cdes'
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
            AND    concat(cs.form_name, (%(cde_delim)s), cs.section_code, (%(cde_delim)s), cs.cde_code) = ANY(%(cde_keys)s);
        """

        summary = {}
        with connections['clinical'].cursor() as cursor:
            cursor.execute(sql, {'cde_delim': settings.FORM_SECTION_DELIMITER, 'cde_keys': cde_keys})
            for row in cursor.fetchall():
                form_name, section_code, max_cnt_sections, cde_code, max_cde_value_cnt = row
                section_cdes = summary.setdefault(form_name, {}).setdefault(section_code, {'count': max_cnt_sections, 'cdes': {}}).get('cdes')
                section_cdes.setdefault(cde_code, {'count': max_cde_value_cnt})

        return summary

    def form_section_cde_sort_order(self, cde_keys):
        sort_order_lookup = {}  # {formkey: {order: 1, sections: {sectionkey: {order: 1, cdes: {cdekey: order: 1}}}}

        for cde_i, cde_key in enumerate(cde_keys):
            form_name, section_code, cde_code = get_form_section_code(cde_key)

            sort_order_lookup.setdefault(form_name, {'order': len(sort_order_lookup), 'sections': {}})
            section_lookup = sort_order_lookup[form_name].get('sections')
            section_lookup.setdefault(section_code, {'order': len(section_lookup), 'cdes': {}})
            cde_lookup = sort_order_lookup[form_name]['sections'][section_code].get('cdes')
            cde_lookup.setdefault(cde_code, len(cde_lookup))

        return sort_order_lookup

    def csv_headers(self, user, report_design):
        # TODO filter patient records by patient filters. If we don't we may get more csv headers than we need.
        # patients = list_patients_query(user,
        #                                report_design.registry.code,
        #                                [cq.code for cq in report_design.filter_consents.all()],
        #                                [wg.id for wg in report_design.filter_working_groups.all()]).values_list("id", flat=True)

        cde_keys = list(report_design.reportclinicaldatafield_set.order_by('id').values_list('cde_key', flat=True))

        # Step 1 - Summarise all clinical data
        cd_summary = self.__clinical_data_summary(cde_keys)

        cfgs_lookup = {}  # e.g. {'cfgcode': {'count': 1, 'heading': 'formatted heading'}}

        # TODO move me
        def get_max_cnt_entries(cfg):
            # TODO can this be nicer?
            max_cnt_entries = \
                RDRFContext.objects.filter(context_form_group=cfg)\
                                   .values('context_form_group', 'object_id')\
                                   .annotate(cnt_entries=Count('object_id')).order_by('-cnt_entries')[:1]

            if max_cnt_entries:
                return max_cnt_entries.first()['cnt_entries']
            else:
                return 1

        # Step 2 - Generate headers from summary
        headers = OrderedDict()

        # Determine ordering
        sort_order_lookup = self.form_section_cde_sort_order(cde_keys)

        # Sort forms by expected order
        sorted_cd_summary = dict(sorted(cd_summary.items(), key=lambda item: sort_order_lookup[item[0]]['order']))

        for form_name, form_data in sorted_cd_summary.items():
            form = RegistryForm.objects.get(name=form_name)
            form_heading = self.__form_heading(form, report_design.cde_heading_format)

            # TODO fix this so we only get the cfgs relevant to the contexts of the clinical data (separate sql TODO)
            for cfg in ContextFormGroup.objects.filter(items__registry_form=form):

                # TODO move to a function
                cfg_lookup = cfgs_lookup.get(cfg.code, None)
                if not cfg_lookup:
                    cfg_lookup = {'count': get_max_cnt_entries(cfg),
                                  'header': self.__cfg_heading(cfg, report_design.cde_heading_format)}
                    cfgs_lookup[cfg.code] = cfg_lookup

                cfg_heading = cfg_lookup["header"]
                longitudinal_entries_cnt = cfg_lookup['count']

                for cfg_i in range(longitudinal_entries_cnt):
                    form_key_prefix, form_label_prefix = self.__form_header_parts(cfg, cfg_heading, cfg_i, form, form_heading)
                    if cfg.is_multiple:
                        headers[f'{form_key_prefix}_key'] = f'{form_label_prefix}_Name'
                        form_key_suffix = '_data'
                    else:
                        form_key_suffix = ''

                    sorted_sections = dict(sorted(form_data.items(), key=lambda item: sort_order_lookup[form_name]['sections'][item[0]]['order']))

                    for section_code, section_data in sorted_sections.items():
                        section = Section.objects.get(code=section_code)
                        section_heading = self.__section_heading(section, report_design.cde_heading_format)
                        for section_i in range(section_data['count']):

                            sorted_cdes = dict(sorted(section_data['cdes'].items(), key=lambda item: sort_order_lookup[form_name]['sections'][section_code]['cdes'][item[0]]))

                            for cde_code, cde_data in sorted_cdes.items():

                                cde = CommonDataElement.objects.get(code=cde_code)
                                cde_heading = self.__cde_heading(cde, report_design.cde_heading_format)
                                cde_key, cde_label = self.__cde_header_parts(form_key_prefix, form_key_suffix,
                                                                             form_label_prefix, section,
                                                                             section_heading, section_i, cde,
                                                                             cde_heading)

                                if cde_data['count'] == 1:
                                    headers[cde_key] = cde_label
                                else:
                                    for cde_i in range(cde_data['count']):
                                        headers.update({f"{cde_key}_{cde_i}": f"{cde_label}_{cde_i + 1}"})
        return headers

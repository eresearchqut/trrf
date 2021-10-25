import pandas as pd
from django.db import connection
import json

p = Patient.objects.all()

formdef = pd.read_sql("""SELECT form.form_id,
       form.form_name,
       section.section_id,
       section.section_name,
       section.section_code,
       cde.code           AS cde_code,
       cde.name           AS cde_name,
       cde.datatype       AS cde_datatype,
       cde.allow_multiple AS cde_allow_multiple,
       cde.is_required AS cde_required,
       cde.max_length as cde_max_length,
       cde.min_value as cde_min_value,
       cde.max_value as cde_max_value,
       cde.pattern as cde_pattern,
       cde.calculation as cde_calculation,
       cde.widget_name AS cde_widget_name,
       cde.widget_settings as cde_widget_settings,
       pvg.pvg_codes,
       pvg.pvg_values
FROM (SELECT id                                    AS form_id,
             name                                  AS form_name,
             regexp_split_to_table(sections, E',') AS section_code
      FROM rdrf_registryform) AS form
         JOIN (SELECT id                                    AS section_id,
                      display_name                          AS section_name,
                      code                                  AS section_code,
                      regexp_split_to_table(elements, E',') AS cde_code
               FROM rdrf_section) AS section
              ON form.section_code = section.section_code
         JOIN rdrf_commondataelement cde ON section.cde_code = cde.code
         LEFT OUTER JOIN (SELECT array_to_string(array_agg(code ORDER BY id), ',')  AS pvg_codes,
                                 array_to_string(array_agg(value ORDER BY id), ',') AS pvg_values,
                                 pv_group_id
                          FROM rdrf_cdepermittedvalue
                          GROUP BY pv_group_id
) AS pvg ON cde.pv_group_id = pvg.pv_group_id""", connection)


cd_records = [];
for record in ClinicalData.objects.filter(collection="cdes").values():
    cd_records.append(record['data'])

with open("/data/output/clinical_data.json", "w") as outfile:
    json.dump(cd_records, outfile)


formdef.to_csv('/data/output/formdef.csv')

print('done')
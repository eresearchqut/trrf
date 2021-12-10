import logging

import pandas as pd

from rdrf.schema.schema import schema

logger = logging.getLogger(__name__)
query=\
"""
query {
  allPatients(registryCode: "ang") {
    id, familyName, givenNames, 
    clinicalDataFlat(cdeKeys: ["NewbornAndInfancyHistory____ANGNewbornInfancyReside____ResideNewborn", "Sleep____ANGBEHDEVSLEEPDIARY____ANGBEHDEVSLEEPDAY", "ChangeInSeizureActivity____SeizureChange____6MoSeizType"])
    	{cfg {name, sortOrder, entryNum}, form, section, sectionCnt,
        cde {
            code
            ... on ClinicalDataCde {value}
            ... on ClinicalDataCdeMultiValue {values}
        } 
    }
  }
}
"""
result = schema.execute(query)
# logger.info(result)

data_allpatients = result.data['allPatients']
logger.info(data_allpatients)

df = pd.json_normalize(data_allpatients,
                       # max_level=1,
                       record_path=['clinicalDataFlat'],
                       meta=['id', 'familyName', 'givenNames'],
                       errors='ignore')


logger.info(df)

df['cde.value'] = df['cde.value'].combine_first(df['cde.values'])
logger.info('after combine:')
logger.info(df)

pivoted = df.pivot(index=['id', 'givenNames', 'familyName'], columns=['cfg.name', 'cfg.sortOrder', 'cfg.entryNum', 'form', 'section', 'sectionCnt', 'cde.code'], values=['cde.value'])
logger.info("Pivoted:")
pivoted = pivoted.sort_index(axis=1, level=['cfg.sortOrder', 'cfg.entryNum', 'form', 'section', 'sectionCnt', 'cde.code'])
pivoted = pivoted.droplevel('cfg.sortOrder', axis=1)
logger.info(pivoted)


transformed = pivoted
# for column in transformed.columns:
#     logger.info(column)
# transformed.columns = ("_".join([column for column in [column_series for column_series in transformed.columns] if column != 'value']))

transformed.columns = transformed.columns.to_series().str.join('_')
transformed.columns = transformed.columns.to_series().str.lstrip('cde.value_')
transformed.reset_index(inplace=True)
transformed = transformed.loc[:, transformed.columns.notnull()] # get rid of null columns (caused by patients with no matching clinical data)
# transformed = transformed.sort_index(axis=1)


logger.info("Transformed:")
logger.info(transformed)

transformed.to_csv('out.csv')
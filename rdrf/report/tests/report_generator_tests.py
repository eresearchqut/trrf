from django.test import TestCase

from rdrf.models.definition.models import Registry, ConsentSection, ConsentQuestion, RegistryForm, Section, \
    CommonDataElement, ContextFormGroup
from registry.groups.models import WorkingGroup
from report.models import ReportDesign, ReportCdeHeadingFormat
from report.reports.generator import Report


class ReportGeneratorTestCase(TestCase):

    maxDiff = None

    def test_humanise_column_labels(self):
        reg_ang = Registry.objects.create(code='ang')
        report_design = ReportDesign.objects.create(registry=reg_ang)
        report = Report(report_design)

        # Fall through logic
        self.assertEqual('Standard column label', report._Report__humanise_column_label('Standard column label'))

        # Patient demographic col headers
        self.assertEqual('Family Name', report._Report__humanise_column_label('familyName'))
        self.assertEqual('Date Of Birth', report._Report__humanise_column_label('dateOfBirth'))
        self.assertEqual('Next Of Kin Relationship', report._Report__humanise_column_label('nextOfKinRelationship { relationship }'))

        # Pivoted col headers
        self.assertEqual('addressType { type }_Patient Address_Address Type',
                         report._Report__humanise_column_label('patientaddressSet_addressType { type }_addressType { type }'))
        self.assertEqual('addressType { type }_Patient Address_Street Address',
                         report._Report__humanise_column_label('patientaddressSet_address_addressType { type }'))
        self.assertEqual('name_Working Groups_Name',
                         report._Report__humanise_column_label('workingGroups_displayName_name'))

    def test_reformat_pivoted_column_labels(self):
        reg_ang = Registry.objects.create(code='ang')
        report_design = ReportDesign.objects.create(registry=reg_ang)
        report = Report(report_design)

        self.assertEqual('SleepGroup_2_Name', report._Report__reformat_pivoted_column_labels('a.cfg.defaultName_SleepGroup_2_a_b_c_d'))
        self.assertEqual('CFG7_1_Sleep_ANGBEHDEVSLEEPDIARY_1_ANGBEHDEVSLEEPDAY',
                         report._Report__reformat_pivoted_column_labels('b.cde.value_CFG7_1_Sleep_ANGBEHDEVSLEEPDIARY_1_ANGBEHDEVSLEEPDAY'))
        self.assertEqual('c.no.match', report._Report__reformat_pivoted_column_labels('c.no.match'))

    def test_graphql_query_minimal_data(self):
        reg_ang = Registry.objects.create(code='ang')
        report_design = ReportDesign.objects.create(registry=reg_ang)
        report = Report(report_design)

        actual = report._Report__get_graphql_query()
        expected = \
            """
            query {
                allPatients(registryCode:"ang",consentQuestionCodes: [],workingGroupIds: []) {
                    id
                    
                    clinicalData(cdeKeys: [])
                    {
                        cfg {code, name, abbreviatedName, defaultName, sortOrder, entryNum},
                        form {name, niceName, abbreviatedName},
                        section {code, name, abbreviatedName, entryNum},
                        cde {
                            code, name, abbreviatedName
                            ... on CdeValueType {value}
                            ... on CdeMultiValueType {values}
                        }
                    }
                }
            }
            """

        self.assertEqual(expected, actual)

    def test_graphql_query_pagination(self):
        reg_ang = Registry.objects.create(code='ang')
        report_design = ReportDesign.objects.create(registry=reg_ang)
        report = Report(report_design)

        actual = report._Report__get_graphql_query(limit=15, offset=30)
        expected = \
            """
            query {
                allPatients(registryCode:"ang",consentQuestionCodes: [],workingGroupIds: [],offset: 30,limit: 15) {
                    id
                    
                    clinicalData(cdeKeys: [])
                    {
                        cfg {code, name, abbreviatedName, defaultName, sortOrder, entryNum},
                        form {name, niceName, abbreviatedName},
                        section {code, name, abbreviatedName, entryNum},
                        cde {
                            code, name, abbreviatedName
                            ... on CdeValueType {value}
                            ... on CdeMultiValueType {values}
                        }
                    }
                }
            }
            """

        self.assertEqual(expected, actual)

    def test_graphql_query_max_data(self):
        reg_ang = Registry.objects.create(code='ang')

        cs1 = ConsentSection.objects.create(registry=reg_ang, code='cs1', section_label='cs1')

        cq1 = ConsentQuestion.objects.create(section=cs1, code='cq1')
        cq2 = ConsentQuestion.objects.create(section=cs1, code='cq2')

        wg1 = WorkingGroup.objects.create(id=1, registry=reg_ang, name='Working Group 1')
        wg2 = WorkingGroup.objects.create(id=2, registry=reg_ang, name='Working Group 2')

        report_design = ReportDesign.objects.create(registry=reg_ang)
        report_design.reportdemographicfield_set.create(model='patient', field='familyName', sort_order=0)
        report_design.reportdemographicfield_set.create(model='patient', field='givenNames', sort_order=1)
        report_design.reportdemographicfield_set.create(model='patientaddressSet', field='state', sort_order=2)
        report_design.reportdemographicfield_set.create(model='patientaddressSet', field='country', sort_order=3)
        report_design.reportdemographicfield_set.create(model='workingGroups', field='name', sort_order=4)

        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____TimeToBed')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____TimeAwake')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____DayOfWeek')

        report_design.filter_consents.add(cq1)
        report_design.filter_consents.add(cq2)

        report_design.filter_working_groups.set([wg1, wg2])

        report = Report(report_design)

        actual = report._Report__get_graphql_query()

        expected = \
            """
            query {
                allPatients(registryCode:"ang",consentQuestionCodes: ["cq1","cq2"],workingGroupIds: ["1","2"]) {
                    id,familyName,givenNames
                    
                    ,patientaddressSet {
                        state,country,addressType { type }
                    }
                
                    ,workingGroups {
                        name
                    }
                
                    clinicalData(cdeKeys: ["SleepForm____SleepSection____DayOfWeek","SleepForm____SleepSection____TimeAwake","SleepForm____SleepSection____TimeToBed"])
                    {
                        cfg {code, name, abbreviatedName, defaultName, sortOrder, entryNum},
                        form {name, niceName, abbreviatedName},
                        section {code, name, abbreviatedName, entryNum},
                        cde {
                            code, name, abbreviatedName
                            ... on CdeValueType {value}
                            ... on CdeMultiValueType {values}
                        }
                    }
                }
            }
            """
        self.assertEqual(expected, actual)

    def test_pre_export_validation(self):
        reg_ang = Registry.objects.create(code='ang')
        CommonDataElement.objects.create(code='TimeToBed', name='Time to bed', abbreviated_name='Time')
        CommonDataElement.objects.create(code='TimeAwake', name='Time Awake in the morning', abbreviated_name='Time')
        CommonDataElement.objects.create(code='DayOfWeek', name='Day of Week', abbreviated_name='Day')
        CommonDataElement.objects.create(code='BestDay', name='Day of Week', abbreviated_name='Best Day')
        Section.objects.create(code='SleepSection', elements='TimeToBed,TimeAwake,DayOfWeek,BestDay', display_name='Sleep', abbreviated_name='SleepSEC')
        form = RegistryForm.objects.create(name='SleepForm', sections='SleepSection', abbreviated_name='SleepFRM', registry=reg_ang)
        cfg = ContextFormGroup.objects.create(registry=reg_ang, code='CFG-1', name='Sleep Group', abbreviated_name='SleepCFG')
        cfg.items.create(registry_form=form)

        report_design = ReportDesign.objects.create(registry=reg_ang)
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____TimeToBed')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____TimeAwake')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____DayOfWeek')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____BestDay')

        # Uses CODE for heading format (guaranteed to be unique)
        report_design.cde_heading_format = ReportCdeHeadingFormat.CODE.value
        report = Report(report_design)

        is_valid, errors = report.validate_for_csv_export()
        self.assertTrue(is_valid)
        self.assertEqual({}, errors)

        # Uses LABEL for heading format
        report_design.cde_heading_format = ReportCdeHeadingFormat.LABEL.value
        report = Report(report_design)

        is_valid, errors = report.validate_for_csv_export()
        self.assertFalse(is_valid)
        self.assertEqual(['Sleep Group_Sleep Form_Sleep_Day of Week'], [*errors['duplicate_headers'].keys()])

        # Uses ABBR_NAME for heading format
        report_design.cde_heading_format = ReportCdeHeadingFormat.ABBR_NAME.value
        report = Report(report_design)

        is_valid, errors = report.validate_for_csv_export()
        self.assertFalse(is_valid)
        self.assertEqual(['SleepCFG_SleepFRM_SleepSEC_Time'], [*errors['duplicate_headers'].keys()])
from django.test import TestCase

from graphql import parse, print_ast

from rdrf.models.definition.models import Registry, ConsentSection, ConsentQuestion, RegistryForm, Section, \
    CommonDataElement, ContextFormGroup
from registry.groups.models import WorkingGroup
from report.models import ReportDesign, ReportCdeHeadingFormat
from report.report_builder import ReportBuilder


class ReportGeneratorTestCase(TestCase):

    maxDiff = None

    def _remove_duplicate_spaces(self, query_str):
        return " ".join(query_str.split())

    def test_graphql_query_minimal_data(self):
        reg_ang = Registry.objects.create(code='ang')
        report_design = ReportDesign.objects.create(registry=reg_ang)
        report = ReportBuilder(report_design)

        actual = report._ReportBuilder__get_graphql_query()
        expected = \
            """
            query {
                patients(registryCode: "ang", consentQuestionCodes: [], workingGroupIds: []) {
                }
            }
            """

        self.assertEqual(self._remove_duplicate_spaces(expected), actual)

    def test_graphql_query_pagination(self):
        reg_ang = Registry.objects.create(code='ang')
        report_design = ReportDesign.objects.create(registry=reg_ang)
        report = ReportBuilder(report_design)

        actual = report._ReportBuilder__get_graphql_query(limit=15, offset=30)
        expected = \
            """
            query {
                patients(registryCode: "ang", consentQuestionCodes: [], workingGroupIds: [], offset: 30, limit: 15) {
                }
            }
            """

        self.assertEqual(self._remove_duplicate_spaces(expected), actual)

    def test_graphql_query_max_data(self):
        reg_ang = Registry.objects.create(code='ang')
        CommonDataElement.objects.create(code='6StartsWithNumber', name='Field starts with number', abbreviated_name='Number field')
        CommonDataElement.objects.create(code='TimeToBed', name='Time to bed', abbreviated_name='Time')
        CommonDataElement.objects.create(code='TimeAwake', name='Time Awake in the morning', abbreviated_name='Time')
        CommonDataElement.objects.create(code='DayOfWeek', name='Day of Week', abbreviated_name='Day')
        Section.objects.create(code='SleepSection', elements='6StartsWithNumber,TimeToBed,TimeAwake,DayOfWeek',
                               display_name='Sleep', abbreviated_name='SleepSEC')
        form = RegistryForm.objects.create(name='SleepForm', sections='SleepSection', abbreviated_name='SleepFRM',
                                           registry=reg_ang)
        cfg = ContextFormGroup.objects.create(registry=reg_ang, code='Sleep', name='Sleep Group',
                                              abbreviated_name='SLE', context_type='M')
        cfg.items.create(registry_form=form)
        CommonDataElement.objects.create(code='ResideNewborn', name='x', abbreviated_name='Newborn')
        CommonDataElement.objects.create(code='ResideInfancy', name='x', abbreviated_name='Infancy')
        Section.objects.create(code='ANGNewbornInfancyReside', elements='ResideNewborn,ResideInfancy',
                               display_name='Reside Newborn/Infancy', abbreviated_name='NewInfReside')
        form = RegistryForm.objects.create(name='NewbornAndInfancyHistory', sections='ANGNewbornInfancyReside', abbreviated_name='NewInfForm',
                                           registry=reg_ang)
        cfg = ContextFormGroup.objects.create(registry=reg_ang, code='History', name='History of Newborn/Infancy',
                                              abbreviated_name='Hist')
        cfg.items.create(registry_form=form)

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

        report_design.reportclinicaldatafield_set.create(cde_key='NewbornAndInfancyHistory____ANGNewbornInfancyReside____ResideNewborn')
        report_design.reportclinicaldatafield_set.create(cde_key='NewbornAndInfancyHistory____ANGNewbornInfancyReside____ResideInfancy')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____DayOfWeek')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____TimeToBed')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____TimeAwake')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____6StartsWithNumber')

        report_design.filter_consents.add(cq1)
        report_design.filter_consents.add(cq2)

        report_design.filter_working_groups.set([wg1, wg2])

        report = ReportBuilder(report_design)

        actual = report._ReportBuilder__get_graphql_query()

        expected = """{
  patients(registryCode: "ang", consentQuestionCodes: ["cq1", "cq2"], workingGroupIds: ["1", "2"]) {
    familyName
    givenNames
    patientaddressSet {
      state
      country
    }
    workingGroups {
      name
    }
    clinicalData {
      History {
        NewbornAndInfancyHistory {
          ANGNewbornInfancyReside {
            ResideNewborn
            ResideInfancy
          }
        }
      }
      Sleep {
        SleepForm {
          key
          data {
            SleepSection {
              DayOfWeek
              TimeToBed
              TimeAwake
              field6StartsWithNumber
            }
          }
        }
      }
    }
  }
}
"""

        # Use formatted query for comparison to help with debugging if assertion fails.
        self.assertEqual(expected, print_ast(parse(actual)))

    def test_pre_export_validation(self):
        reg_ang = Registry.objects.create(code='ang')
        CommonDataElement.objects.create(code='TimeToBed', name='Time to bed', abbreviated_name='Time')
        CommonDataElement.objects.create(code='TimeAwake', name='Time Awake in the morning', abbreviated_name='Time')
        CommonDataElement.objects.create(code='DayOfWeek', name='Day of Week', abbreviated_name='Day')
        CommonDataElement.objects.create(code='BestDay', name='Day of Week', abbreviated_name='Best Day')
        Section.objects.create(code='SleepSection', elements='TimeToBed,TimeAwake,DayOfWeek,BestDay', display_name='Sleep', abbreviated_name='SleepSEC')
        form = RegistryForm.objects.create(name='SleepForm', sections='SleepSection', abbreviated_name='SleepFRM', registry=reg_ang)
        cfg = ContextFormGroup.objects.create(registry=reg_ang, code='CFG1', name='Sleep Group', abbreviated_name='SleepCFG')
        cfg.items.create(registry_form=form)

        report_design = ReportDesign.objects.create(registry=reg_ang)
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____TimeToBed')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____TimeAwake')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____DayOfWeek')
        report_design.reportclinicaldatafield_set.create(cde_key='SleepForm____SleepSection____BestDay')

        # Uses CODE for heading format (guaranteed to be unique)
        report_design.cde_heading_format = ReportCdeHeadingFormat.CODE.value
        report = ReportBuilder(report_design)

        is_valid, errors = report.validate_for_csv_export()
        self.assertTrue(is_valid)
        self.assertEqual({}, errors)

        # Uses LABEL for heading format
        report_design.cde_heading_format = ReportCdeHeadingFormat.LABEL.value
        report = ReportBuilder(report_design)

        is_valid, errors = report.validate_for_csv_export()
        self.assertFalse(is_valid)
        self.assertEqual(['Sleep Group_Sleep Form_Sleep_Day of Week'], [*errors['duplicate_headers'].keys()])

        # Uses ABBR_NAME for heading format
        report_design.cde_heading_format = ReportCdeHeadingFormat.ABBR_NAME.value
        report = ReportBuilder(report_design)

        is_valid, errors = report.validate_for_csv_export()
        self.assertFalse(is_valid)
        self.assertEqual(['SleepCFG_SleepFRM_SleepSEC_Time'], [*errors['duplicate_headers'].keys()])
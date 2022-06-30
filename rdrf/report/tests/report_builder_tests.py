from collections import OrderedDict
from datetime import datetime

from django.test import TestCase
from graphql import parse, print_ast

from rdrf.models.definition.models import Registry, ConsentSection, ConsentQuestion, RegistryForm, Section, \
    CommonDataElement, ContextFormGroup
from registry.groups.models import WorkingGroup, CustomUser
from registry.patients.models import Patient, AddressType
from report.models import ReportDesign, ReportCdeHeadingFormat
from report.report_builder import ReportBuilder


class ReportGeneratorTestCase(TestCase):

    maxDiff = None

    def _remove_duplicate_spaces(self, query_str):
        return " ".join(query_str.split())

    def _request(self):
        class TestContext:
            user = CustomUser.objects.create(username="admin", is_staff=True, is_superuser=True)
        return TestContext()

    def test_graphql_query_minimal_data(self):
        reg_ang = Registry.objects.create(code='ang')
        report_design = ReportDesign.objects.create(registry=reg_ang)
        report = ReportBuilder(report_design)

        actual = report._get_graphql_query(self._request())
        expected = \
            """
            query {
                allPatients(registryCode: "ang", consentQuestionCodes: [], workingGroupIds: []) {
                    patients {
                    }
                }
            }
            """

        self.assertEqual(self._remove_duplicate_spaces(expected), actual)

    def test_graphql_query_pagination(self):
        reg_ang = Registry.objects.create(code='ang')
        report_design = ReportDesign.objects.create(registry=reg_ang)
        report = ReportBuilder(report_design)

        actual = report._get_graphql_query(self._request(), limit=15, offset=30)
        expected = \
            """
            query {
                allPatients(registryCode: "ang", consentQuestionCodes: [], workingGroupIds: []) {
                    patients(offset: 30, limit: 15) {
                    }
                }
            }
            """

        self.assertEqual(self._remove_duplicate_spaces(expected), actual)


    def test_graphql_query_pivot_fields(self):
        reg_ang = Registry.objects.create(code='ang')
        cs1 = ConsentSection.objects.create(registry=reg_ang, code='cs1', section_label='cs1')
        ConsentQuestion.objects.create(section=cs1, code='angConsent1', position=1)
        ConsentQuestion.objects.create(section=cs1, code='angConsent2', position=2)
        ConsentQuestion.objects.create(section=cs1, code='angConsent3', position=3)
        ConsentQuestion.objects.create(section=cs1, code='angConsent4', position=4)

        report_design = ReportDesign.objects.create(registry=reg_ang)
        report_design.reportdemographicfield_set.create(model='patient', field='id', sort_order=0)
        report_design.reportdemographicfield_set.create(model='consents', field='answer', sort_order=0)
        report_design.reportdemographicfield_set.create(model='consents', field='firstSave', sort_order=0)
        report = ReportBuilder(report_design)

        actual = report._get_graphql_query(self._request())
        expected = """{
  allPatients(registryCode: "ang", consentQuestionCodes: [], workingGroupIds: []) {
    patients {
      id
      consents {
        angConsent1 {
          firstSave
          answer
        }
        angConsent2 {
          firstSave
          answer
        }
        angConsent3 {
          firstSave
          answer
        }
        angConsent4 {
          firstSave
          answer
        }
      }
    }
  }
}
"""
        # Use formatted query for comparison to help with debugging if assertion fails.
        self.assertEqual(expected, print_ast(parse(actual)))

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
        cfg_sleep = ContextFormGroup.objects.create(registry=reg_ang, code='Sleep', name='Sleep Group',
                                              abbreviated_name='SLE', context_type='M')
        cfg_sleep.items.create(registry_form=form)
        CommonDataElement.objects.create(code='ResideNewborn', name='x', abbreviated_name='Newborn')
        CommonDataElement.objects.create(code='ResideInfancy', name='x', abbreviated_name='Infancy')
        Section.objects.create(code='ANGNewbornInfancyReside', elements='ResideNewborn,ResideInfancy',
                               display_name='Reside Newborn/Infancy', abbreviated_name='NewInfReside')
        form = RegistryForm.objects.create(name='NewbornAndInfancyHistory', sections='ANGNewbornInfancyReside', abbreviated_name='NewInfForm',
                                           registry=reg_ang)
        cfg_history = ContextFormGroup.objects.create(registry=reg_ang, code='History', name='History of Newborn/Infancy',
                                              abbreviated_name='Hist')
        cfg_history.items.create(registry_form=form)

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

        report_design.reportclinicaldatafield_set.create(context_form_group=cfg_history, cde_key='NewbornAndInfancyHistory____ANGNewbornInfancyReside____ResideNewborn')
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg_history, cde_key='NewbornAndInfancyHistory____ANGNewbornInfancyReside____ResideInfancy')
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg_sleep, cde_key='SleepForm____SleepSection____DayOfWeek')
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg_sleep, cde_key='SleepForm____SleepSection____TimeToBed')
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg_sleep, cde_key='SleepForm____SleepSection____TimeAwake')
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg_sleep, cde_key='SleepForm____SleepSection____6StartsWithNumber')

        report_design.filter_consents.add(cq1)
        report_design.filter_consents.add(cq2)

        report_design.filter_working_groups.set([wg1, wg2])

        report = ReportBuilder(report_design)

        actual = report._get_graphql_query(self._request())

        expected = """{
  allPatients(registryCode: "ang", consentQuestionCodes: ["cq1", "cq2"], workingGroupIds: ["1", "2"]) {
    patients {
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
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg, cde_key='SleepForm____SleepSection____TimeToBed')
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg, cde_key='SleepForm____SleepSection____TimeAwake')
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg, cde_key='SleepForm____SleepSection____DayOfWeek')
        report_design.reportclinicaldatafield_set.create(context_form_group=cfg, cde_key='SleepForm____SleepSection____BestDay')

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

    def test_get_demographic_headers(self):
        def setup_test_data():
            self.registry = Registry.objects.create(code='REG')
            self.registry_with_no_consent_questions = Registry.objects.create(code='REG2')

            cs1 = ConsentSection.objects.create(registry=self.registry, code='CS1', section_label='Consent Section 1')
            ConsentQuestion.objects.create(code='CQ1', section=cs1, position=1)
            ConsentQuestion.objects.create(code='CQ2', section=cs1, position=2)

            p1 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))
            p1.rdrf_registry.set([self.registry, self.registry_with_no_consent_questions])
            address_type_home = AddressType.objects.create(type='Home')
            address_type_postal = AddressType.objects.create(type='Postal')
            p1.patientaddress_set.create(address_type=address_type_home)
            p1.patientaddress_set.create(address_type=address_type_postal)

        setup_test_data()
        request = self._request()

        report_design = ReportDesign.objects.create(registry=self.registry)
        report_design.reportdemographicfield_set.create(sort_order=1, model='patient', field='id')
        report_design.reportdemographicfield_set.create(sort_order=2, model='patient', field='familyName')
        report_design.reportdemographicfield_set.create(sort_order=3, model='patient', field='nextOfKinRelationship { relationship }')

        report_design.reportdemographicfield_set.create(sort_order=4, model='patientaddressSet', field='addressType { type }')
        report_design.reportdemographicfield_set.create(sort_order=5, model='patientaddressSet', field='address')
        report_design.reportdemographicfield_set.create(sort_order=6, model='patientaddressSet', field='suburb')

        report_design.reportdemographicfield_set.create(sort_order=7, model='consents', field='answer')
        report_design.reportdemographicfield_set.create(sort_order=8, model='consents', field='firstSave')
        report_design.reportdemographicfield_set.create(sort_order=9, model='consents', field='lastUpdate')

        actual = ReportBuilder(report_design)._get_demographic_headers(request)
        expected = OrderedDict({'id': 'ID',
                                'familyName': 'Family Name',
                                'nextOfKinRelationship_relationship': 'Next Of Kin Relationship',
                                'patientaddressSet_0_addressType_type': 'Patient Address_1_Address Type',
                                'patientaddressSet_0_address': 'Patient Address_1_Street Address',
                                'patientaddressSet_0_suburb': 'Patient Address_1_Suburb',
                                'patientaddressSet_1_addressType_type': 'Patient Address_2_Address Type',
                                'patientaddressSet_1_address': 'Patient Address_2_Street Address',
                                'patientaddressSet_1_suburb': 'Patient Address_2_Suburb',
                                'consents_CQ1_answer': 'Consents_CQ1_Answer',
                                'consents_CQ1_firstSave': 'Consents_CQ1_Date of First Save',
                                'consents_CQ1_lastUpdate': 'Consents_CQ1_Date of Last Update',
                                'consents_CQ2_answer': 'Consents_CQ2_Answer',
                                'consents_CQ2_firstSave': 'Consents_CQ2_Date of First Save',
                                'consents_CQ2_lastUpdate': 'Consents_CQ2_Date of Last Update',
                                })

        self.assertDictEqual(expected, actual)

        # Test 2 - pivoted model has no variants
        report_design.registry = self.registry_with_no_consent_questions
        report_design.save()
        actual = ReportBuilder(report_design)._get_demographic_headers(request)
        expected = OrderedDict({'id': 'ID',
                                'familyName': 'Family Name',
                                'nextOfKinRelationship_relationship': 'Next Of Kin Relationship',
                                'patientaddressSet_0_addressType_type': 'Patient Address_1_Address Type',
                                'patientaddressSet_0_address': 'Patient Address_1_Street Address',
                                'patientaddressSet_0_suburb': 'Patient Address_1_Suburb',
                                'patientaddressSet_1_addressType_type': 'Patient Address_2_Address Type',
                                'patientaddressSet_1_address': 'Patient Address_2_Street Address',
                                'patientaddressSet_1_suburb': 'Patient Address_2_Suburb',
                                'consents_answer': 'Consents_Answer',
                                'consents_firstSave': 'Consents_Date of First Save',
                                'consents_lastUpdate': 'Consents_Date of Last Update',
                                })

        self.assertDictEqual(expected, actual)


from collections import OrderedDict
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from rdrf.models.definition.models import Registry, ClinicalData, CommonDataElement, Section, RegistryForm, \
    ContextFormGroup, RDRFContext
from registry.groups.models import CustomUser
from registry.patients.models import Patient
from report.models import ReportDesign, ReportCdeHeadingFormat
from report.reports.clinical_data_report_util import ClinicalDataReportUtil


class ClinicalDataGeneratorTestCase(TestCase):

    databases = ['default', 'clinical']
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        # Setup for standard forms/sections & cdes
        cls.registry = Registry.objects.create(code="ang")
        CommonDataElement.objects.create(code='lieFlat', abbreviated_name='Lie Flat', name="I can lie flat")
        CommonDataElement.objects.create(code='needHelp', abbreviated_name='Need Help', name="I need help to")
        CommonDataElement.objects.create(code='mndNeedUse', abbreviated_name='Need Help', name="I need help to")
        Section.objects.create(code='inBed', elements='lieFlat,needHelp,mndNeedUse', abbreviated_name='In Bed',
                               display_name='When I am in bed:')
        form1 = RegistryForm.objects.create(name='firstVisit', sections='inBed', registry=cls.registry,
                                            abbreviated_name='first visit')

        CommonDataElement.objects.create(code='breathHard', abbreviated_name='Short breath',
                                         name="Shortness of breath")
        CommonDataElement.objects.create(code='breathAssist', abbreviated_name='Breathing Assistance',
                                         name="The following helps relieve my breathing")
        Section.objects.create(code='breathing', elements='breathHard,breathAssist', abbreviated_name='Breathing',
                               display_name='Breathing')
        form2 = RegistryForm.objects.create(name='myBreathing', sections='breathing', registry=cls.registry,
                                            abbreviated_name='My Breathing')

        CommonDataElement.objects.create(code='apptDate', abbreviated_name='Appt Date', name="Appointment Date")
        CommonDataElement.objects.create(code='apptTime', abbreviated_name='Appt Time', name="Appointment Time")
        Section.objects.create(code='apptList', elements='apptDate,apptTime', abbreviated_name='Appointment List',
                               display_name='Appointment List')
        form3 = RegistryForm.objects.create(name='myAppointments', sections='apptList', registry=cls.registry,
                                            abbreviated_name='My Appointments')

        cfg1 = ContextFormGroup.objects.create(code='clinicalVisit', registry=cls.registry, name='Clinical Visit',
                                               context_type="F", abbreviated_name="Clinical", sort_order=1)
        cfg1.items.create(registry_form=form1)
        cfg1.items.create(registry_form=form2)
        cfg1.items.create(registry_form=form3)

        # Setup for longitudinal
        CommonDataElement.objects.create(code='completedDate', abbreviated_name='Completed Date',
                                         name="Completed Date")
        CommonDataElement.objects.create(code='fatigue', abbreviated_name='Fatigue', name="Fatigue")
        CommonDataElement.objects.create(code='pain', abbreviated_name='Pain', name="Pain")
        Section.objects.create(code='symptoms', elements='completedDate,fatigue,pain', abbreviated_name='Symptoms',
                               display_name='Symptoms')
        form4 = RegistryForm.objects.create(name='recentSymptoms', sections='symptoms', registry=cls.registry,
                                            abbreviated_name='Recent Symptoms')

        cfg2 = ContextFormGroup.objects.create(code='symptoms', registry=cls.registry, name='Symptoms',
                                               context_type="M", abbreviated_name="Symptoms", sort_order=2)
        cfg2.items.create(registry_form=form4)

        # Setup for multisection & multi cde values
        CommonDataElement.objects.create(code='timeToBed', abbreviated_name='Bed Time', name="Time to Bed")
        CommonDataElement.objects.create(code='timesAwoke', abbreviated_name='Times Awoke',
                                         name="Times Awoke during the night", allow_multiple=True)
        Section.objects.create(code='sleepDiary', elements='timeToBed,timesAwoke', abbreviated_name='Sleep Diary',
                               display_name='Sleep Diary', allow_multiple=True)
        form5 = RegistryForm.objects.create(name='sleep', sections='sleepDiary', registry=cls.registry,
                                            abbreviated_name='Sleep')

        cfg3 = ContextFormGroup.objects.create(code='sleepTracking', registry=cls.registry, name='Sleep Tracking',
                                               context_type="F", abbreviated_name="Sleep Tracking", sort_order=3)
        cfg3.items.create(registry_form=form5)

        # Create clinical data
        p1 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))
        p1.rdrf_registry.set([cls.registry])
        p2 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))
        p2.rdrf_registry.set([cls.registry])
        
        c_type = ContentType.objects.get_for_model(p1)
        ctx1 = RDRFContext.objects.create(context_form_group=cfg1, registry=cls.registry, content_type=c_type,
                                          object_id=p1.id)
        ctx2 = RDRFContext.objects.create(context_form_group=cfg2, registry=cls.registry, content_type=c_type,
                                          object_id=p1.id)
        ctx3 = RDRFContext.objects.create(context_form_group=cfg2, registry=cls.registry, content_type=c_type,
                                          object_id=p1.id)
        ctx4 = RDRFContext.objects.create(context_form_group=cfg3, registry=cls.registry, content_type=c_type,
                                          object_id=p1.id)

        data = {
            "forms": [
                {
                    "name": "firstVisit",
                    "sections": [
                        {
                            "code": "inBed",
                            "cdes": [
                                {"code": "lieFlat", "value": "5"},
                                {"code": "needHelp", "value": ""},
                                {"code": "mndNeedUse", "value": ""}
                            ]
                        }
                    ]
                },
                {
                    "name": "myBreathing",
                    "sections": [
                        {
                            "code": "breathing",
                            "cdes": [
                                {"code": "breathHard", "value": "3"},
                                {"code": "breathAssist", "value": "oxygen"}
                            ]
                        }
                    ]
                }
            ]
        }
        ClinicalData.objects.create(registry_code='ang', django_id=p1.id, django_model='Patient',
                                    collection="cdes", context_id=ctx1.id, data=data)

        longitudinal_1 = {
            "forms": [
                {
                    "name": "recentSymptoms",
                    "sections": [
                        {
                            "code": "symptoms",
                            "cdes": [
                                {"code": "completedDate", "value": "2022-02-07"},
                                {"code": "fatigue", "value": "4"},
                                {"code": "pain", "value": "1"}
                            ]
                        }
                    ]
                }
            ]
        }

        ClinicalData.objects.create(registry_code='ang', django_id=p1.id, django_model='Patient',
                                    collection="cdes",
                                    context_id=ctx2.id, data=longitudinal_1)

        longitudinal_2 = {
            "forms": [
                {
                    "name": "recentSymptoms",
                    "sections": [
                        {
                            "code": "symptoms",
                            "cdes": [
                                {"code": "completedDate", "value": "2022-02-08"},
                                {"code": "fatigue", "value": "3"},
                                {"code": "pain", "value": "2"}
                            ]
                        }
                    ]
                }
            ]
        }

        ClinicalData.objects.create(registry_code='ang', django_id=p1.id, django_model='Patient',
                                    collection="cdes",
                                    context_id=ctx3.id, data=longitudinal_2)

        multisection_data = {
            "forms": [
                {
                    "name": "sleep",
                    "sections": [
                        {
                            "code": "sleepDiary",
                            "allow_multiple": True,
                            "cdes": [
                                [
                                    {"code": "timeToBed", "value": "9:55pm"},
                                    {"code": "timesAwoke", "value": ["1:00am", "3:00am"]}
                                ],
                                [
                                    {"code": "timeToBed", "value": "8:45pm"},
                                    {"code": "timesAwoke", "value": ["11:45pm", "5:30am"]}
                                ]
                            ]
                        }
                    ]
                }
            ]
        }

        ClinicalData.objects.create(registry_code='ang', django_id=p1.id, django_model='Patient',
                                    collection="cdes",
                                    context_id=ctx4.id, data=multisection_data)

    def test_form_section_cde_sort_order(self):
        generator = ClinicalDataReportUtil()

        cde_keys = ['sleep____sleepDiary____timeToBed', 'sleep____sleepDiary____timesAwoke',
                    'recentSymptoms____symptoms____completedDate', 'recentSymptoms____symptoms____fatigue',
                    'recentSymptoms____symptoms____pain', 'sleep____sleepDiary____dayOfWeek',
                    'sleep____generalSleep____sleepConditions']

        expected_sort_order = \
            {'sleep': {'order': 0, 'sections': {'sleepDiary': { 'order': 0,
                                                                'cdes': {'timeToBed': 0,
                                                                         'timesAwoke': 1,
                                                                         'dayOfWeek': 2}},
                                                'generalSleep': {'order': 1, 'cdes': {'sleepConditions': 0}}}},
             'recentSymptoms': {'order': 1, 'sections': {'symptoms': {'order': 0,
                                                                      'cdes': {'completedDate': 0,
                                                                               'fatigue': 1,
                                                                               'pain': 2}}}}}

        sort_order = generator._ClinicalDataReportUtil__form_section_cde_sort_order(cde_keys)

        self.assertEqual(sort_order, expected_sort_order)


    def test_generate_csv_headers(self):
        report_design = ReportDesign.objects.create(registry=self.registry)
        report_design.reportclinicaldatafield_set.create(id=1, cde_key='sleep____sleepDiary____timeToBed')
        report_design.reportclinicaldatafield_set.create(id=2, cde_key='sleep____sleepDiary____timesAwoke')
        report_design.reportclinicaldatafield_set.create(id=3, cde_key='recentSymptoms____symptoms____completedDate')
        report_design.reportclinicaldatafield_set.create(id=4, cde_key='recentSymptoms____symptoms____fatigue')
        report_design.reportclinicaldatafield_set.create(id=5, cde_key='recentSymptoms____symptoms____pain')

        user = CustomUser.objects.create(username="admin", is_staff=True, is_superuser=True)

        generator = ClinicalDataReportUtil()

        report_design.cde_heading_format = ReportCdeHeadingFormat.CODE.value
        expected = OrderedDict()
        expected.update({
            'clinicalData_sleepTracking_sleep_sleepDiary_0_timeToBed': 'sleepTracking_sleep_sleepDiary_1_timeToBed',
            'clinicalData_sleepTracking_sleep_sleepDiary_0_timesAwoke_0': 'sleepTracking_sleep_sleepDiary_1_timesAwoke_1',
            'clinicalData_sleepTracking_sleep_sleepDiary_0_timesAwoke_1': 'sleepTracking_sleep_sleepDiary_1_timesAwoke_2',
            'clinicalData_sleepTracking_sleep_sleepDiary_1_timeToBed': 'sleepTracking_sleep_sleepDiary_2_timeToBed',
            'clinicalData_sleepTracking_sleep_sleepDiary_1_timesAwoke_0': 'sleepTracking_sleep_sleepDiary_2_timesAwoke_1',
            'clinicalData_sleepTracking_sleep_sleepDiary_1_timesAwoke_1': 'sleepTracking_sleep_sleepDiary_2_timesAwoke_2',
            'clinicalData_symptoms_recentSymptoms_0_key': 'symptoms_recentSymptoms_1_Name',
            'clinicalData_symptoms_recentSymptoms_0_data_symptoms_completedDate': 'symptoms_recentSymptoms_1_symptoms_completedDate',
            'clinicalData_symptoms_recentSymptoms_0_data_symptoms_fatigue': 'symptoms_recentSymptoms_1_symptoms_fatigue',
            'clinicalData_symptoms_recentSymptoms_0_data_symptoms_pain': 'symptoms_recentSymptoms_1_symptoms_pain',
            'clinicalData_symptoms_recentSymptoms_1_key': 'symptoms_recentSymptoms_2_Name',
            'clinicalData_symptoms_recentSymptoms_1_data_symptoms_completedDate': 'symptoms_recentSymptoms_2_symptoms_completedDate',
            'clinicalData_symptoms_recentSymptoms_1_data_symptoms_fatigue': 'symptoms_recentSymptoms_2_symptoms_fatigue',
            'clinicalData_symptoms_recentSymptoms_1_data_symptoms_pain': 'symptoms_recentSymptoms_2_symptoms_pain'
        })


        actual = generator.csv_headers(user, report_design)
        print("** actual **")
        print(actual)
        self.assertEqual(actual, expected)
from collections import OrderedDict
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from rdrf.models.definition.models import Registry, ClinicalData, CommonDataElement, Section, RegistryForm, \
    ContextFormGroup, RDRFContext
from registry.groups.models import CustomUser
from registry.patients.models import Patient
from report.models import ReportDesign, ReportCdeHeadingFormat
from report.clinical_data_csv_util import ClinicalDataCsvUtil


class ClinicalDataGeneratorTestCase(TestCase):

    databases = ['default', 'clinical']
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        # Setup for standard forms/sections & cdes
        cls.registry = Registry.objects.create(code="ang")

        registry_definition = [
            {'name': 'firstVisit', 'abbreviated_name': 'first visit', 'sections': [{
                'code': 'inBed', 'abbreviated_name': 'Need Help', 'display_name': 'I need help to',
                'cdes': [{'code': 'lieFlat', 'abbreviated_name': 'Lie Flat', 'name': "I can lie flat"},
                         {'code': 'needHelp', 'abbreviated_name': 'Need Help', 'name': "I need help to"},
                         {'code': 'mndNeedUse', 'abbreviated_name': 'Need Help', 'name': "I need help to"}]}
            ]},
            {'name': 'myBreathing', 'abbreviated_name': 'My Breathing', 'sections': [{
                'code': 'breathing', 'abbreviated_name': 'Breathing', 'display_name': 'Breathing',
                'cdes': [{'code': 'breathHard', 'abbreviated_name': 'Short Breath', 'name': 'Shortness of breath'},
                         {'code': 'breathAssist', 'abbreviated_name': 'Breathing Assistance', 'name': 'The following helps relieve my breathing'}]}
            ]},
            {'name': 'myAppointments', 'abbreviated_name': 'My Appointments', 'sections': [{
                'code': 'apptList', 'abbreviated_name': 'Appointment List', 'display_name': 'Appointment List',
                'cdes': [{'code': 'apptDate', 'abbreviated_name': 'Appt Date', 'name': 'Appointment Date'},
                         {'code': 'apptTime', 'abbreviated_name': 'Appt Time', 'name': 'Appointment Time'}]}
            ]},
            {'name': 'recentSymptoms', 'abbreviated_name': 'Recent Symptoms', 'sections': [
                {'code': 'symptoms', 'abbreviated_name': 'Symptoms', 'display_name': 'Symptoms',
                 'cdes': [{'code': 'completedDate', 'abbreviated_name': 'Completed Date', 'name': 'Completed Date'},
                          {'code': 'fatigue', 'abbreviated_name': 'Fatigue', 'name': 'Fatigue'},
                          {'code': 'pain', 'abbreviated_name': 'Pain', 'name': 'Pain'}]},
                {'code': 'otherSymptoms', 'abbreviated_name': 'Other Symptoms', 'display_name': 'Other Symptoms',
                 'cdes': [{'code': 'energy', 'abbreviated_name': 'Energy', 'name': 'Energy'}]}
            ]},
            {'name': 'sleep', 'abbreviated_name': 'Sleep', 'sections': [{
                'code': 'sleepDiary', 'abbreviated_name': 'Sleep Diary', 'display_name': 'Sleep Diary', 'allow_multiple': True,
                'cdes': [{'code': 'timeToBed', 'abbreviated_name': 'Bed Time', 'name': 'Time to Bed'},
                         {'code': 'timesAwoke', 'abbreviated_name': 'Times Awoke', 'name': 'Times Awoke during the night', 'allow_multiple': True},
                         {'code': 'difficulty', 'abbreviated_name': 'Difficulty', 'name': 'Any difficulties'}]}
            ]},
            {'name': 'infancy', 'abbreviated_name': 'Infancy', 'sections': [{
                'code': 'growth', 'abbreviated_name': 'Growth', 'display_name': 'Growth and Development',
                'cdes': [{'code': 'weight6mo', 'abbreviated_name': 'Weight at 6mo', 'name': 'Weight at 6 months old'}]}
            ]},
        ]

        # Create objects from definition
        for form in registry_definition:
            for section in form['sections']:
                for cde in section['cdes']:
                    CommonDataElement.objects.create(code=cde['code'], abbreviated_name=cde['abbreviated_name'], name=cde['name'], allow_multiple=cde.get('allow_multiple', False))
                Section.objects.create(code=section['code'], abbreviated_name=section['abbreviated_name'], display_name=section['display_name'],
                                       allow_multiple=section.get('allow_multiple', False),
                                       elements=','.join([cde['code'] for cde in section['cdes']]))
            RegistryForm.objects.create(name=form['name'], registry=cls.registry, abbreviated_name=form['abbreviated_name'],
                                        sections=','.join([section['code'] for section in form['sections']]))

        # Context Form Groups
        cfg_clinical_visit = ContextFormGroup.objects.create(code='clinicalVisit', registry=cls.registry,
                                                             name='Clinical Visit', context_type="F",
                                                             abbreviated_name="Clinical", sort_order=1)
        cfg_clinical_visit.items.create(registry_form=RegistryForm.objects.get(name='firstVisit'))
        cfg_clinical_visit.items.create(registry_form=RegistryForm.objects.get(name='myBreathing'))
        cfg_clinical_visit.items.create(registry_form=RegistryForm.objects.get(name='myAppointments'))
        cfg_clinical_visit.items.create(registry_form=RegistryForm.objects.get(name='infancy'))

        cfg_symptoms = ContextFormGroup.objects.create(code='symptoms', registry=cls.registry, name='Symptoms',
                                                       context_type="M", abbreviated_name="Symptoms", sort_order=2)
        cfg_symptoms.items.create(registry_form=RegistryForm.objects.get(name='recentSymptoms'))

        cfg_sleep = ContextFormGroup.objects.create(code='sleepTracking', registry=cls.registry, name='Sleep Tracking',
                                               context_type="F", abbreviated_name="Sleep Tracking", sort_order=3)
        cfg_sleep.items.create(registry_form=RegistryForm.objects.get(name='sleep'))


        # Create clinical data
        p1 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))
        p1.rdrf_registry.set([cls.registry])
        p2 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))
        p2.rdrf_registry.set([cls.registry])
        
        c_type = ContentType.objects.get_for_model(p1)
        ctx1 = RDRFContext.objects.create(context_form_group=cfg_clinical_visit, registry=cls.registry, content_type=c_type,
                                          object_id=p1.id)
        ctx2 = RDRFContext.objects.create(context_form_group=cfg_symptoms, registry=cls.registry, content_type=c_type,
                                          object_id=p1.id)
        ctx3 = RDRFContext.objects.create(context_form_group=cfg_symptoms, registry=cls.registry, content_type=c_type,
                                          object_id=p1.id)
        ctx4 = RDRFContext.objects.create(context_form_group=cfg_sleep, registry=cls.registry, content_type=c_type,
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
        generator = ClinicalDataCsvUtil()

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

        sort_order = generator._ClinicalDataCsvUtil__form_section_cde_sort_order(cde_keys)

        self.assertEqual(sort_order, expected_sort_order)


    def test_generate_csv_headers(self):
        report_design = ReportDesign.objects.create(registry=self.registry)
        report_design.reportclinicaldatafield_set.create(id=1, cde_key='sleep____sleepDiary____timeToBed')
        report_design.reportclinicaldatafield_set.create(id=2, cde_key='sleep____sleepDiary____timesAwoke')
        report_design.reportclinicaldatafield_set.create(id=3, cde_key='sleep____sleepDiary____difficulty')
        report_design.reportclinicaldatafield_set.create(id=4, cde_key='recentSymptoms____symptoms____completedDate')
        report_design.reportclinicaldatafield_set.create(id=5, cde_key='recentSymptoms____symptoms____fatigue')
        report_design.reportclinicaldatafield_set.create(id=6, cde_key='recentSymptoms____otherSymptoms____energy')
        report_design.reportclinicaldatafield_set.create(id=7, cde_key='recentSymptoms____symptoms____pain')
        report_design.reportclinicaldatafield_set.create(id=8, cde_key='infancy____growth____weight6mo')

        user = CustomUser.objects.create(username="admin", is_staff=True, is_superuser=True)

        generator = ClinicalDataCsvUtil()

        report_design.cde_heading_format = ReportCdeHeadingFormat.CODE.value
        expected = OrderedDict({
            'clinicalData_sleepTracking_sleep_sleepDiary_0_timeToBed': 'sleepTracking_sleep_sleepDiary_1_timeToBed',
            'clinicalData_sleepTracking_sleep_sleepDiary_0_timesAwoke_0': 'sleepTracking_sleep_sleepDiary_1_timesAwoke_1',
            'clinicalData_sleepTracking_sleep_sleepDiary_0_timesAwoke_1': 'sleepTracking_sleep_sleepDiary_1_timesAwoke_2',
            'clinicalData_sleepTracking_sleep_sleepDiary_0_difficulty': 'sleepTracking_sleep_sleepDiary_1_difficulty',
            'clinicalData_sleepTracking_sleep_sleepDiary_1_timeToBed': 'sleepTracking_sleep_sleepDiary_2_timeToBed',
            'clinicalData_sleepTracking_sleep_sleepDiary_1_timesAwoke_0': 'sleepTracking_sleep_sleepDiary_2_timesAwoke_1',
            'clinicalData_sleepTracking_sleep_sleepDiary_1_timesAwoke_1': 'sleepTracking_sleep_sleepDiary_2_timesAwoke_2',
            'clinicalData_sleepTracking_sleep_sleepDiary_1_difficulty': 'sleepTracking_sleep_sleepDiary_2_difficulty',
            'clinicalData_symptoms_recentSymptoms_0_key': 'symptoms_recentSymptoms_1_Name',
            'clinicalData_symptoms_recentSymptoms_0_data_symptoms_completedDate': 'symptoms_recentSymptoms_1_symptoms_completedDate',
            'clinicalData_symptoms_recentSymptoms_0_data_symptoms_fatigue': 'symptoms_recentSymptoms_1_symptoms_fatigue',
            'clinicalData_symptoms_recentSymptoms_0_data_symptoms_pain': 'symptoms_recentSymptoms_1_symptoms_pain',
            'clinicalData_symptoms_recentSymptoms_0_data_otherSymptoms_energy': 'symptoms_recentSymptoms_1_otherSymptoms_energy',
            'clinicalData_symptoms_recentSymptoms_1_key': 'symptoms_recentSymptoms_2_Name',
            'clinicalData_symptoms_recentSymptoms_1_data_symptoms_completedDate': 'symptoms_recentSymptoms_2_symptoms_completedDate',
            'clinicalData_symptoms_recentSymptoms_1_data_symptoms_fatigue': 'symptoms_recentSymptoms_2_symptoms_fatigue',
            'clinicalData_symptoms_recentSymptoms_1_data_symptoms_pain': 'symptoms_recentSymptoms_2_symptoms_pain',
            'clinicalData_symptoms_recentSymptoms_1_data_otherSymptoms_energy': 'symptoms_recentSymptoms_2_otherSymptoms_energy',
            'clinicalData_clinicalVisit_infancy_growth_weight6mo': 'clinicalVisit_infancy_growth_weight6mo',
        })

        actual = generator.csv_headers(user, report_design)
        self.assertEqual(actual, expected)

    def test_generate_csv_headers_no_clinical_data(self):
        report_design = ReportDesign.objects.create(registry=self.registry)
        report_design.reportclinicaldatafield_set.create(id=1, cde_key='sleep____sleepDiary____difficulty')
        report_design.reportclinicaldatafield_set.create(id=2, cde_key='recentSymptoms____otherSymptoms____energy')
        report_design.reportclinicaldatafield_set.create(id=3, cde_key='infancy____growth____weight6mo')

        user = CustomUser.objects.create(username="admin", is_staff=True, is_superuser=True)

        generator = ClinicalDataCsvUtil()

        report_design.cde_heading_format = ReportCdeHeadingFormat.CODE.value
        expected = OrderedDict({
            'clinicalData_sleepTracking_sleep_sleepDiary_0_difficulty': 'sleepTracking_sleep_sleepDiary_1_difficulty',
            'clinicalData_symptoms_recentSymptoms_0_key': 'symptoms_recentSymptoms_1_Name',
            'clinicalData_symptoms_recentSymptoms_0_data_otherSymptoms_energy': 'symptoms_recentSymptoms_1_otherSymptoms_energy',
            'clinicalData_symptoms_recentSymptoms_1_key': 'symptoms_recentSymptoms_2_Name',
            'clinicalData_symptoms_recentSymptoms_1_data_otherSymptoms_energy': 'symptoms_recentSymptoms_2_otherSymptoms_energy',
            'clinicalData_clinicalVisit_infancy_growth_weight6mo': 'clinicalVisit_infancy_growth_weight6mo',
        })

        actual = generator.csv_headers(user, report_design)
        self.assertEqual(actual, expected)
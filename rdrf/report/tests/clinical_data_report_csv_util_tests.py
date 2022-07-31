import logging
from collections import OrderedDict
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from rdrf.models.definition.models import Registry, ClinicalData, CommonDataElement, Section, RegistryForm, \
    ContextFormGroup, RDRFContext
from registry.groups.models import CustomUser
from registry.patients.models import Patient
from report.clinical_data_csv_util import ClinicalDataCsvUtil
from report.models import ReportDesign, ReportCdeHeadingFormat


class ClinicalDataGeneratorTestCase(TestCase):

    databases = ['default', 'clinical']
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create(username="admin", is_staff=True, is_superuser=True)

        # Setup for standard forms/sections & cdes
        cls.registry = Registry.objects.create(code="ang")

        registry_definition = [
            {'name': 'myHealth', 'abbreviated_name': 'first visit', 'sections': [{
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
        cls.cfg_clinical_visit = ContextFormGroup.objects.create(code='clinicalVisit', registry=cls.registry,
                                                             name='Clinical Visit', context_type="F",
                                                             abbreviated_name="Clinical", sort_order=1)
        cls.cfg_clinical_visit.items.create(registry_form=RegistryForm.objects.get(name='myHealth'))
        cls.cfg_clinical_visit.items.create(registry_form=RegistryForm.objects.get(name='myBreathing'))
        cls.cfg_clinical_visit.items.create(registry_form=RegistryForm.objects.get(name='myAppointments'))
        cls.cfg_clinical_visit.items.create(registry_form=RegistryForm.objects.get(name='infancy'))

        cls.cfg_symptoms = ContextFormGroup.objects.create(code='symptoms', registry=cls.registry, name='Symptoms',
                                                       context_type="M", abbreviated_name="Symptoms", sort_order=2)
        cls.cfg_symptoms.items.create(registry_form=RegistryForm.objects.get(name='recentSymptoms'))

        cls.cfg_sleep = ContextFormGroup.objects.create(code='sleepTracking', registry=cls.registry, name='Sleep Tracking',
                                               context_type="F", abbreviated_name="Sleep Tracking", sort_order=3)
        cls.cfg_sleep.items.create(registry_form=RegistryForm.objects.get(name='sleep'))
        
        cls.cfg_tracking = ContextFormGroup.objects.create(code='ongoing', registry=cls.registry,
                                                           name='Clinical Visit', context_type='M', abbreviated_name='initial', sort_order=4)
        cls.cfg_tracking.items.create(registry_form=RegistryForm.objects.get(name='myHealth'))


        # Create clinical data
        p1 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))
        p2 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))
        p3 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))

        for p in (p1, p2, p3):
            p.rdrf_registry.set([cls.registry])
        
        c_type = ContentType.objects.get_for_model(p1)
        p1_ctx1 = RDRFContext.objects.create(context_form_group=cls.cfg_clinical_visit, registry=cls.registry,
                                             content_type=c_type, object_id=p1.id)
        p1_ctx2 = RDRFContext.objects.create(context_form_group=cls.cfg_symptoms, registry=cls.registry,
                                             content_type=c_type, object_id=p1.id)
        p1_ctx3 = RDRFContext.objects.create(context_form_group=cls.cfg_symptoms, registry=cls.registry,
                                             content_type=c_type, object_id=p1.id)
        p1_ctx4 = RDRFContext.objects.create(context_form_group=cls.cfg_sleep, registry=cls.registry,
                                             content_type=c_type, object_id=p1.id)

        data = {
            "forms": [
                {
                    "name": "myHealth",
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
                                    collection="cdes", context_id=p1_ctx1.id, data=data)

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
                                    context_id=p1_ctx2.id, data=longitudinal_1)

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
                                    context_id=p1_ctx3.id, data=longitudinal_2)

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
                                    context_id=p1_ctx4.id, data=multisection_data)

        p3_data_tracking_1 = {
            "forms": [
                {
                    "name": "myHealth",
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
                }
            ]
        }

        p3_data_tracking_2 = {
            "forms": [
                {
                    "name": "myHealth",
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
                }
            ]
        }

        p3_data_tracking_3 = {
            "forms": [
                {
                    "name": "myHealth",
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
                }
            ]
        }

        for data in (p3_data_tracking_1, p3_data_tracking_2, p3_data_tracking_3):
            context = RDRFContext.objects.create(context_form_group=cls.cfg_tracking, registry=cls.registry,
                                                 content_type=ContentType.objects.get_for_model(p3), object_id=p3.id)
            ClinicalData.objects.create(registry_code='ang', django_id=p3.id, django_model='Patient', collection="cdes",
                                        context_id=context.id, data=data)



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

        sort_order = generator._form_section_cde_sort_order(cde_keys)

        self.assertEqual(sort_order, expected_sort_order)


    def test_generate_csv_headers(self):
        report_design = ReportDesign.objects.create(registry=self.registry)
        report_design.reportclinicaldatafield_set.create(id=1, cde_key='sleep____sleepDiary____timeToBed', context_form_group=self.cfg_sleep)
        report_design.reportclinicaldatafield_set.create(id=2, cde_key='sleep____sleepDiary____timesAwoke', context_form_group=self.cfg_sleep)
        report_design.reportclinicaldatafield_set.create(id=3, cde_key='sleep____sleepDiary____difficulty', context_form_group=self.cfg_sleep)
        report_design.reportclinicaldatafield_set.create(id=4, cde_key='recentSymptoms____symptoms____completedDate', context_form_group=self.cfg_symptoms)
        report_design.reportclinicaldatafield_set.create(id=5, cde_key='recentSymptoms____symptoms____fatigue', context_form_group=self.cfg_symptoms)
        report_design.reportclinicaldatafield_set.create(id=6, cde_key='recentSymptoms____otherSymptoms____energy', context_form_group=self.cfg_symptoms)
        report_design.reportclinicaldatafield_set.create(id=7, cde_key='recentSymptoms____symptoms____pain', context_form_group=self.cfg_symptoms)
        report_design.reportclinicaldatafield_set.create(id=8, cde_key='infancy____growth____weight6mo', context_form_group=self.cfg_clinical_visit)

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

        actual = generator.csv_headers(self.user, report_design)
        self.assertEqual(actual, expected)

    def test_generate_csv_headers_no_clinical_data(self):
        report_design = ReportDesign.objects.create(registry=self.registry)
        report_design.reportclinicaldatafield_set.create(id=1, cde_key='sleep____sleepDiary____difficulty', context_form_group=self.cfg_sleep)
        report_design.reportclinicaldatafield_set.create(id=2, cde_key='recentSymptoms____otherSymptoms____energy', context_form_group=self.cfg_symptoms)
        report_design.reportclinicaldatafield_set.create(id=3, cde_key='infancy____growth____weight6mo', context_form_group=self.cfg_clinical_visit)

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

        actual = generator.csv_headers(self.user, report_design)
        self.assertEqual(actual, expected)

    def test_generate_csv_headers_for_cde_in_multiple_cfgs(self):
        # Test 1 - Configured for items within a longitudinal CFG
        util = ClinicalDataCsvUtil()
        report_design = ReportDesign.objects.create(registry=self.registry, cde_heading_format=ReportCdeHeadingFormat.CODE.value)
        report_design.reportclinicaldatafield_set.create(id=1, cde_key='myHealth____inBed____lieFlat', context_form_group=self.cfg_tracking)
        report_design.reportclinicaldatafield_set.create(id=2, cde_key='myHealth____inBed____needHelp', context_form_group=self.cfg_tracking)
        report_design.reportclinicaldatafield_set.create(id=3, cde_key='myHealth____inBed____mndNeedUse', context_form_group=self.cfg_tracking)

        expected = OrderedDict({
            'clinicalData_ongoing_myHealth_0_key': 'ongoing_myHealth_1_Name',
            'clinicalData_ongoing_myHealth_0_data_inBed_lieFlat': 'ongoing_myHealth_1_inBed_lieFlat',
            'clinicalData_ongoing_myHealth_0_data_inBed_needHelp': 'ongoing_myHealth_1_inBed_needHelp',
            'clinicalData_ongoing_myHealth_0_data_inBed_mndNeedUse': 'ongoing_myHealth_1_inBed_mndNeedUse',
            'clinicalData_ongoing_myHealth_1_key': 'ongoing_myHealth_2_Name',
            'clinicalData_ongoing_myHealth_1_data_inBed_lieFlat': 'ongoing_myHealth_2_inBed_lieFlat',
            'clinicalData_ongoing_myHealth_1_data_inBed_needHelp': 'ongoing_myHealth_2_inBed_needHelp',
            'clinicalData_ongoing_myHealth_1_data_inBed_mndNeedUse': 'ongoing_myHealth_2_inBed_mndNeedUse',
            'clinicalData_ongoing_myHealth_2_key': 'ongoing_myHealth_3_Name',
            'clinicalData_ongoing_myHealth_2_data_inBed_lieFlat': 'ongoing_myHealth_3_inBed_lieFlat',
            'clinicalData_ongoing_myHealth_2_data_inBed_needHelp': 'ongoing_myHealth_3_inBed_needHelp',
            'clinicalData_ongoing_myHealth_2_data_inBed_mndNeedUse': 'ongoing_myHealth_3_inBed_mndNeedUse',
        })

        self.assertEqual(util.csv_headers(self.user, report_design), expected)

        # Test 2 - Configured for same items but within a fixed CFG
        for cde_field in report_design.reportclinicaldatafield_set.all():
            cde_field.context_form_group = self.cfg_clinical_visit
            cde_field.save()

        expected = OrderedDict({
            'clinicalData_clinicalVisit_myHealth_inBed_lieFlat': 'clinicalVisit_myHealth_inBed_lieFlat',
            'clinicalData_clinicalVisit_myHealth_inBed_needHelp': 'clinicalVisit_myHealth_inBed_needHelp',
            'clinicalData_clinicalVisit_myHealth_inBed_mndNeedUse': 'clinicalVisit_myHealth_inBed_mndNeedUse'
        })

        self.assertEqual(util.csv_headers(self.user, report_design), expected)

    def test_generate_csv_headers_with_form_timestamp(self):
        report_design = ReportDesign.objects.create(registry=self.registry)
        report_design.reportclinicaldatafield_set.create(id=1, cde_key='sleep____sleepDiary____timeToBed', context_form_group=self.cfg_sleep)
        report_design.reportclinicaldatafield_set.create(id=2, cde_key='recentSymptoms____symptoms____completedDate', context_form_group=self.cfg_symptoms)
        report_design.reportclinicaldatafield_set.create(id=3, cde_key='recentSymptoms____otherSymptoms____energy', context_form_group=self.cfg_symptoms)
        report_design.reportclinicaldatafield_set.create(id=4, cde_key='infancy____growth____weight6mo', context_form_group=self.cfg_clinical_visit)

        generator = ClinicalDataCsvUtil()

        report_design.cde_heading_format = ReportCdeHeadingFormat.CODE.value
        report_design.cde_include_form_timestamp = True
        expected = OrderedDict({
            'clinicalData_sleepTracking_sleep_lastUpdated': 'sleepTracking_sleep_Last Updated',
            'clinicalData_sleepTracking_sleep_sleepDiary_0_timeToBed': 'sleepTracking_sleep_sleepDiary_1_timeToBed',
            'clinicalData_sleepTracking_sleep_sleepDiary_1_timeToBed': 'sleepTracking_sleep_sleepDiary_2_timeToBed',
            'clinicalData_symptoms_recentSymptoms_0_key': 'symptoms_recentSymptoms_1_Name',
            'clinicalData_symptoms_recentSymptoms_0_lastUpdated': 'symptoms_recentSymptoms_1_Last Updated',
            'clinicalData_symptoms_recentSymptoms_0_data_symptoms_completedDate': 'symptoms_recentSymptoms_1_symptoms_completedDate',
            'clinicalData_symptoms_recentSymptoms_0_data_otherSymptoms_energy': 'symptoms_recentSymptoms_1_otherSymptoms_energy',
            'clinicalData_symptoms_recentSymptoms_1_key': 'symptoms_recentSymptoms_2_Name',
            'clinicalData_symptoms_recentSymptoms_1_lastUpdated': 'symptoms_recentSymptoms_2_Last Updated',
            'clinicalData_symptoms_recentSymptoms_1_data_symptoms_completedDate': 'symptoms_recentSymptoms_2_symptoms_completedDate',
            'clinicalData_symptoms_recentSymptoms_1_data_otherSymptoms_energy': 'symptoms_recentSymptoms_2_otherSymptoms_energy',
            'clinicalData_clinicalVisit_infancy_lastUpdated': 'clinicalVisit_infancy_Last Updated',
            'clinicalData_clinicalVisit_infancy_growth_weight6mo': 'clinicalVisit_infancy_growth_weight6mo',
        })

        actual = generator.csv_headers(self.user, report_design)
        self.assertEqual(actual, expected)


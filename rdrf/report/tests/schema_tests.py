from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from rdrf.models.definition.models import Registry, ClinicalData, ContextFormGroup, RDRFContext, RegistryForm, Section, \
    CommonDataElement
from report.schema.schema import PatientType
from registry.patients.models import Patient


class PatientSchemaTest(TestCase):

    databases = ['default', 'clinical']
    maxDiff = None

    def test_resolve_sex(self):
        def resolve_sex_for_patient_with(sex):
            patient_type = PatientType()
            patient_type.sex = sex
            return patient_type.resolve_sex(None)
        self.assertEqual("Male", resolve_sex_for_patient_with("1"))
        self.assertEqual("Female", resolve_sex_for_patient_with("2"))
        self.assertEqual("Indeterminate", resolve_sex_for_patient_with("3"))
        self.assertEqual("10", resolve_sex_for_patient_with("10"))

    def test_resolve_clinical_data(self):
        
        def setup_test_registry_and_clinical_data(p1):
            reg_ang = Registry.objects.create(code="ang")

            # Setup for standard forms/sections & cdes
            CommonDataElement.objects.create(code='lieFlat', abbreviated_name='Lie Flat', name="I can lie flat")
            CommonDataElement.objects.create(code='needHelp', abbreviated_name='Need Help', name="I need help to")
            CommonDataElement.objects.create(code='mndNeedUse', abbreviated_name='Need Help', name="I need help to")
            Section.objects.create(code='inBed', elements='lieFlat,needHelp', abbreviated_name='In Bed', display_name='When I am in bed:')
            form1 = RegistryForm.objects.create(name='firstVisit', sections='inBed', registry=reg_ang, abbreviated_name='first visit')
    
            CommonDataElement.objects.create(code='breathHard', abbreviated_name='Short breath', name="Shortness of breath")
            CommonDataElement.objects.create(code='breathAssist', abbreviated_name='Breathing Assistance', name="The following helps relieve my breathing")
            Section.objects.create(code='breathing', elements='breathHard,breathAssist', abbreviated_name='Breathing', display_name='Breathing')
            form2 = RegistryForm.objects.create(name='myBreathing', sections='breathing', registry=reg_ang, abbreviated_name='My Breathing')
    
            CommonDataElement.objects.create(code='apptDate', abbreviated_name='Appt Date', name="Appointment Date")
            CommonDataElement.objects.create(code='apptTime', abbreviated_name='Appt Time', name="Appointment Time")
            Section.objects.create(code='apptList', elements='apptDate,apptTime', abbreviated_name='Appointment List', display_name='Appointment List')
            form3 = RegistryForm.objects.create(name='myAppointments', sections='apptList', registry=reg_ang, abbreviated_name='My Appointments')

            cfg1 = ContextFormGroup.objects.create(code='clinicalVisit', registry=reg_ang, name='Clinical Visit', naming_scheme="M", abbreviated_name="Clinical", sort_order=1)
            cfg1.items.create(registry_form=form1)
            cfg1.items.create(registry_form=form2)
            cfg1.items.create(registry_form=form3)
    
            # Setup for longitudinal
            CommonDataElement.objects.create(code='completedDate', abbreviated_name='Completed Date', name="Completed Date")
            CommonDataElement.objects.create(code='fatigue', abbreviated_name='Fatigue', name="Fatigue")
            CommonDataElement.objects.create(code='pain', abbreviated_name='Pain', name="Pain")
            Section.objects.create(code='symptoms', elements='completedDate,fatigue,pain', abbreviated_name='Symptoms', display_name='Symptoms')
            form4 = RegistryForm.objects.create(name='recentSymptoms', sections='symptoms', registry=reg_ang, abbreviated_name='Recent Symptoms')

            cfg2 = ContextFormGroup.objects.create(code='symptoms', registry=reg_ang, name='Symptoms', naming_scheme="M", abbreviated_name="Symptoms", sort_order=2)
            cfg2.items.create(registry_form=form4)
            
            # Setup for multisection & multi cde values
            CommonDataElement.objects.create(code='timeToBed', abbreviated_name='Bed Time', name="Time to Bed")
            CommonDataElement.objects.create(code='timesAwoke', abbreviated_name='Times Awoke', name="Times Awoke during the night")
            Section.objects.create(code='sleepDiary', elements='timeToBed,timesAwoke', abbreviated_name='Sleep Diary', display_name='Sleep Diary')
            form5 = RegistryForm.objects.create(name='sleep', sections='sleepDiary', registry=reg_ang, abbreviated_name='Sleep')
    
            cfg3 = ContextFormGroup.objects.create(code='sleepTracking', registry=reg_ang, name='Sleep Tracking', naming_scheme="M", abbreviated_name="Sleep Tracking", sort_order=3)
            cfg3.items.create(registry_form=form5)
    
            # Create clinical data
            c_type = ContentType.objects.get_for_model(p1)
            ctx1 = RDRFContext.objects.create(context_form_group=cfg1, registry=reg_ang, content_type=c_type, object_id=1)
            ctx2 = RDRFContext.objects.create(context_form_group=cfg2, registry=reg_ang, content_type=c_type, object_id=2)
            ctx3 = RDRFContext.objects.create(context_form_group=cfg2, registry=reg_ang, content_type=c_type, object_id=3)
            ctx4 = RDRFContext.objects.create(context_form_group=cfg3, registry=reg_ang, content_type=c_type, object_id=4)

            data = {"forms": [{"name":"firstVisit",
                               "sections": [{"code": "inBed",
                                             "cdes": [
                                                 {"code": "lieFlat", "value": "5"},
                                                 {"code": "needHelp", "value": ""},
                                                 {"code": "mndNeedUse", "value": ""}
                                             ]}
                                            ]},
                              {"name":"myBreathing",
                               "sections": [{"code": "breathing",
                                             "cdes": [
                                                 {"code": "breathHard", "value": "3"},
                                                 {"code": "breathAssist", "value": "oxygen"}
                                             ]}]}
                              ]}
            ClinicalData.objects.create(registry_code='ang', django_id=p1.id, django_model='Patient', collection="cdes", context_id=ctx1.id, data=data)
    
            longitudinal_1 = {"forms": [{"name": "recentSymptoms",
                                            "sections": [{"code": "symptoms",
                                                          "cdes":
                                                              [{"code": "completedDate", "value": "2022-02-07"},
                                                               {"code": "fatigue", "value": "4"},
                                                               {"code": "pain", "value": "1"}]}]
                                            }]
                                 }
    
            ClinicalData.objects.create(registry_code='ang', django_id=p1.id, django_model='Patient', collection="cdes",
                                        context_id=ctx2.id, data=longitudinal_1)
    
            longitudinal_2 = {"forms": [{"name": "recentSymptoms",
                                            "sections": [{"code": "symptoms",
                                                          "cdes":
                                                              [{"code": "completedDate", "value": "2022-02-08"},
                                                               {"code": "fatigue", "value": "3"},
                                                               {"code": "pain", "value": "2"}]}]
                                            }]
                                 }
    
            ClinicalData.objects.create(registry_code='ang', django_id=p1.id, django_model='Patient', collection="cdes",
                                        context_id=ctx3.id, data=longitudinal_2)

            multisection_data = {"forms": [{"name": "sleep",
                                            "sections": [{"code": "sleepDiary",
                                                          "allow_multiple": True,
                                                          "cdes": [
                                                              [{"code": "timeToBed", "value": "9:55pm"},
                                                               {"code": "timesAwoke", "value": ["1:00am", "3:00am"]}],
                                                              [{"code": "timeToBed", "value": "8:45pm"},
                                                               {"code": "timesAwoke", "value": ["11:45pm", "5:30am"]}]
                                                          ]}]
                                            }]
                                 }

            ClinicalData.objects.create(registry_code='ang', django_id=p1.id, django_model='Patient', collection="cdes",
                                        context_id=ctx4.id, data=multisection_data)


        p1 = Patient.objects.create(consent=True, date_of_birth=datetime(1980, 4, 11))
        patient_type = PatientType()
        patient_type.id = p1.id

        self.assertEqual([{}], patient_type.resolve_clinical_data(None))

        setup_test_registry_and_clinical_data(p1)
        
        # No cde keys supplied should render an empty response
        self.assertEqual([{}], patient_type.resolve_clinical_data(None))

        # Same, but this time with cde_keys
        expected = [{'cfg': {'code': 'clinicalVisit', 'name': 'Clinical Visit', 'default_name': 'Modules', 'abbreviated_name': 'Clinical', 'sort_order': 1, 'entry_num': 1},
                    'form': {'abbreviated_name': 'first visit', 'name': 'firstVisit' , 'nice_name': 'First Visit'},
                    'section': {'abbreviated_name': 'In Bed', 'code': 'inBed', 'entry_num': 1, 'name': 'When I am in bed:'},
                    'cde': {'abbreviated_name': 'Lie Flat', 'code': 'lieFlat', 'name': 'I can lie flat', 'value': '5'}},
                    {'cfg': {'code': 'clinicalVisit', 'name': 'Clinical Visit', 'default_name': 'Modules', 'abbreviated_name': 'Clinical', 'sort_order': 1, 'entry_num': 1},
                     'form': {'abbreviated_name': 'first visit', 'name': 'firstVisit', 'nice_name': 'First Visit'},
                     'section': {'abbreviated_name': 'In Bed', 'code': 'inBed', 'entry_num': 1,
                                 'name': 'When I am in bed:'},
                     'cde': {'abbreviated_name': 'Need Help', 'code': 'needHelp', 'name': 'I need help to', 'value': ''}},
                    {'cfg': {'code': 'clinicalVisit', 'name': 'Clinical Visit', 'default_name': 'Modules', 'abbreviated_name': 'Clinical', 'sort_order': 1, 'entry_num': 1},
                     'form': {'abbreviated_name': 'My Breathing', 'name': 'myBreathing', 'nice_name': 'My Breathing'},
                     'section': {'abbreviated_name': 'Breathing', 'code': 'breathing', 'entry_num': 1, 'name': 'Breathing'},
                     'cde': {'abbreviated_name': 'Breathing Assistance', 'code': 'breathAssist', 'name': 'The following helps relieve my breathing', 'value': 'oxygen'}}
                    ]
        self.assertEqual(expected, patient_type.resolve_clinical_data(None, ['firstVisit____inBed____lieFlat', 
                                                                             'firstVisit____inBed____needHelp', 
                                                                             'myBreathing____breathing____breathAssist']))

        # Longitudinal
        expected = [{'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 1},
                    'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                    'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                    'cde': {'abbreviated_name': 'Completed Date', 'code': 'completedDate', 'name': 'Completed Date', 'value': '2022-02-07'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 1},
                     'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                     'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                     'cde': {'abbreviated_name': 'Fatigue', 'code': 'fatigue', 'name': 'Fatigue', 'value': '4'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 1},
                     'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                     'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                     'cde': {'abbreviated_name': 'Pain', 'code': 'pain', 'name': 'Pain', 'value': '1'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 2},
                    'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                    'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                    'cde': {'abbreviated_name': 'Completed Date', 'code': 'completedDate', 'name': 'Completed Date', 'value': '2022-02-08'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 2},
                     'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                     'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                     'cde': {'abbreviated_name': 'Fatigue', 'code': 'fatigue', 'name': 'Fatigue', 'value': '3'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 2},
                     'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                     'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                     'cde': {'abbreviated_name': 'Pain', 'code': 'pain', 'name': 'Pain', 'value': '2'}}]
        self.assertEqual(expected, patient_type.resolve_clinical_data(None, ['recentSymptoms____symptoms____completedDate',
                                                                             'recentSymptoms____symptoms____fatigue',
                                                                             'recentSymptoms____symptoms____pain']))

        # Mixed longitudinal and single entry data
        expected = [{'cfg': {'code': 'clinicalVisit', 'name': 'Clinical Visit', 'default_name': 'Modules', 'abbreviated_name': 'Clinical', 'sort_order': 1, 'entry_num': 1},
                     'form': {'abbreviated_name': 'first visit', 'name': 'firstVisit', 'nice_name': 'First Visit'},
                     'section': {'abbreviated_name': 'In Bed', 'code': 'inBed', 'entry_num': 1, 'name': 'When I am in bed:'},
                     'cde': {'abbreviated_name': 'Lie Flat', 'code': 'lieFlat', 'name': 'I can lie flat', 'value': '5'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 1},
                    'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                    'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                    'cde': {'abbreviated_name': 'Completed Date', 'code': 'completedDate', 'name': 'Completed Date', 'value': '2022-02-07'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 1},
                     'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                     'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                     'cde': {'abbreviated_name': 'Fatigue', 'code': 'fatigue', 'name': 'Fatigue', 'value': '4'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 2},
                    'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                    'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                    'cde': {'abbreviated_name': 'Completed Date', 'code': 'completedDate', 'name': 'Completed Date', 'value': '2022-02-08'}},
                    {'cfg': {'code': 'symptoms', 'name': 'Symptoms', 'default_name': 'Modules', 'abbreviated_name': 'Symptoms', 'sort_order': 2, 'entry_num': 2},
                     'form': {'abbreviated_name': 'Recent Symptoms',  'name': 'recentSymptoms', 'nice_name': 'Recent Symptoms'},
                     'section': {'abbreviated_name': 'Symptoms', 'code': 'symptoms', 'entry_num': 1, 'name': 'Symptoms'},
                     'cde': {'abbreviated_name': 'Fatigue', 'code': 'fatigue', 'name': 'Fatigue', 'value': '3'}}]
        self.assertEqual(expected,
                         patient_type.resolve_clinical_data(None, ['recentSymptoms____symptoms____completedDate',
                                                                   'recentSymptoms____symptoms____fatigue',
                                                                   'firstVisit____inBed____lieFlat']))

        # Multisection & Multi value
        expected = [{'cfg': {'code': 'sleepTracking', 'name': 'Sleep Tracking', 'default_name': 'Modules', 'abbreviated_name': 'Sleep Tracking', 'sort_order': 3, 'entry_num': 1},
                     'form': {'abbreviated_name': 'Sleep', 'name': 'sleep', 'nice_name': 'Sleep'},
                     'section': {'abbreviated_name': 'Sleep Diary', 'code': 'sleepDiary', 'entry_num': 1, 'name': 'Sleep Diary'},
                     'cde': {'abbreviated_name': 'Bed Time', 'code': 'timeToBed', 'name': 'Time to Bed', 'value': '9:55pm'}},
                    {'cfg': {'code': 'sleepTracking', 'name': 'Sleep Tracking', 'default_name': 'Modules', 'abbreviated_name': 'Sleep Tracking', 'sort_order': 3, 'entry_num': 1},
                     'form': {'abbreviated_name': 'Sleep', 'name': 'sleep', 'nice_name': 'Sleep'},
                     'section': {'abbreviated_name': 'Sleep Diary', 'code': 'sleepDiary', 'entry_num': 1, 'name': 'Sleep Diary'},
                     'cde': {'abbreviated_name': 'Times Awoke', 'code': 'timesAwoke', 'name': 'Times Awoke during the night', 'value': ['1:00am', '3:00am']}},
                    {'cfg': {'code': 'sleepTracking', 'name': 'Sleep Tracking', 'default_name': 'Modules', 'abbreviated_name': 'Sleep Tracking', 'sort_order': 3, 'entry_num': 1},
                     'form': {'abbreviated_name': 'Sleep', 'name': 'sleep', 'nice_name': 'Sleep'},
                     'section': {'abbreviated_name': 'Sleep Diary', 'code': 'sleepDiary', 'entry_num': 2, 'name': 'Sleep Diary'},
                     'cde': {'abbreviated_name': 'Bed Time', 'code': 'timeToBed', 'name': 'Time to Bed', 'value': '8:45pm'}},
                    {'cfg': {'code': 'sleepTracking', 'name': 'Sleep Tracking', 'default_name': 'Modules', 'abbreviated_name': 'Sleep Tracking', 'sort_order': 3, 'entry_num': 1},
                     'form': {'abbreviated_name': 'Sleep', 'name': 'sleep', 'nice_name': 'Sleep'},
                     'section': {'abbreviated_name': 'Sleep Diary', 'code': 'sleepDiary', 'entry_num': 2, 'name': 'Sleep Diary'},
                     'cde': {'abbreviated_name': 'Times Awoke', 'code': 'timesAwoke', 'name': 'Times Awoke during the night', 'value': ['11:45pm', '5:30am']}}]
        self.assertEqual(expected,
                         patient_type.resolve_clinical_data(None, ['sleep____sleepDiary____timeToBed',
                                                                   'sleep____sleepDiary____timesAwoke']))
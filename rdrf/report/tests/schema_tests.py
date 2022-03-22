from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from graphene.test import Client

from rdrf.models.definition.models import Registry, ClinicalData, ContextFormGroup, RDRFContext, RegistryForm, Section, \
    CommonDataElement
from registry.groups.models import CustomUser, WorkingGroup
from registry.patients.models import Patient, AddressType
from report.schema.schema import create_dynamic_schema


class SchemaTest(TestCase):
    databases = ['default', 'clinical']
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.registry = Registry.objects.create(code="test")

        class TestContext:
            user = CustomUser.objects.create(username="admin", is_staff=True, is_superuser=True)

        cls.query_context = TestContext()

    def test_query_data_summary_max_address_count(self):
        create_patient = lambda: Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))

        # Setup address types
        type_home = AddressType.objects.create(type='Home')
        type_postal = AddressType.objects.create(type='Postal')
        type_secondary = AddressType.objects.create(type='Secondary')

        p1 = create_patient()
        p2 = create_patient()
        p3 = create_patient()

        p1.rdrf_registry.set([self.registry])
        p2.rdrf_registry.set([self.registry])
        p3.rdrf_registry.set([Registry.objects.create(code='another')])

        client = Client(create_dynamic_schema())
        query = """
        {
            dataSummary(registryCode: "test") {
                maxAddressCount
            }
        }
        """

        # No addresses
        result = client.execute(query, context_value=self.query_context)
        self.assertEqual({"data": {"dataSummary": {"maxAddressCount": 0}}}, result)

        # Patients with varying number of addresses across different registries
        p1.patientaddress_set.create(address_type=type_home).save()
        p2.patientaddress_set.create(address_type=type_home).save()
        p2.patientaddress_set.create(address_type=type_postal).save()
        p3.patientaddress_set.create(address_type=type_home).save()
        p3.patientaddress_set.create(address_type=type_postal).save()
        p3.patientaddress_set.create(address_type=type_secondary).save()

        result = client.execute(query, context_value=self.query_context)
        self.assertEqual({"data": {"dataSummary": {"maxAddressCount": 2}}}, result)

    def test_query_data_summary_max_working_group_count(self):
        create_patient = lambda: Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))

        # Setup working groups
        wg1 = WorkingGroup.objects.create(name="WG1")
        wg2 = WorkingGroup.objects.create(name="WG2")
        wg3 = WorkingGroup.objects.create(name="WG3")
        wg4 = WorkingGroup.objects.create(name="WG3")

        p1 = create_patient()
        p2 = create_patient()
        p3 = create_patient()
        p4 = create_patient()

        p1.rdrf_registry.set([self.registry])
        p2.rdrf_registry.set([self.registry])
        p3.rdrf_registry.set([Registry.objects.create(code='another')])
        p4.rdrf_registry.set([self.registry])

        client = Client(create_dynamic_schema())
        query = """
        {
            dataSummary(registryCode: "test") {
                maxWorkingGroupCount
            }
        }
        """

        # No working groups assigned to patients yet
        result = client.execute(query, context_value=self.query_context)
        self.assertEqual({"data": {"dataSummary": {"maxWorkingGroupCount": 0}}}, result)

        # Patients with varying number of addresses across different registries
        p1.working_groups.set([wg1])
        p2.working_groups.set([wg2, wg3])
        p3.working_groups.set([wg1, wg2, wg3, wg4])
        p4.working_groups.set([wg1, wg2, wg3])

        result = client.execute(query, context_value=self.query_context)
        self.assertEqual({"data": {"dataSummary": {"maxWorkingGroupCount": 3}}}, result)

    def test_query_sex(self):
        patients = [
            Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="1"),
            Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="2"),
            Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="3"),
        ]

        for patient in patients:
            patient.rdrf_registry.set([self.registry])

        client = Client(create_dynamic_schema())

        result = client.execute("""
        {
          patients(registryCode: "test") {
            sex
          }
        }
        """, context_value=self.query_context)

        self.assertEqual({
            "data": {
                "patients": [
                    {
                        "sex": "Male"
                    },
                    {
                        "sex": "Female"
                    },
                    {
                        "sex": "Indeterminate"
                    }
                ]
            }
        }, result)

    def test_query_clinical_data(self):
        def setup_test_registry_and_clinical_data(patient):
            # Setup for standard forms/sections & cdes
            CommonDataElement.objects.create(code='lieFlat', abbreviated_name='Lie Flat', name="I can lie flat")
            CommonDataElement.objects.create(code='needHelp', abbreviated_name='Need Help', name="I need help to")
            CommonDataElement.objects.create(code='mndNeedUse', abbreviated_name='Need Help', name="I need help to")
            Section.objects.create(code='inBed', elements='lieFlat,needHelp', abbreviated_name='In Bed',
                                   display_name='When I am in bed:')
            form1 = RegistryForm.objects.create(name='firstVisit', sections='inBed', registry=self.registry,
                                                abbreviated_name='first visit')

            CommonDataElement.objects.create(code='breathHard', abbreviated_name='Short breath',
                                             name="Shortness of breath")
            CommonDataElement.objects.create(code='breathAssist', abbreviated_name='Breathing Assistance',
                                             name="The following helps relieve my breathing")
            Section.objects.create(code='breathing', elements='breathHard,breathAssist', abbreviated_name='Breathing',
                                   display_name='Breathing')
            form2 = RegistryForm.objects.create(name='myBreathing', sections='breathing', registry=self.registry,
                                                abbreviated_name='My Breathing')

            CommonDataElement.objects.create(code='apptDate', abbreviated_name='Appt Date', name="Appointment Date")
            CommonDataElement.objects.create(code='apptTime', abbreviated_name='Appt Time', name="Appointment Time")
            Section.objects.create(code='apptList', elements='apptDate,apptTime', abbreviated_name='Appointment List',
                                   display_name='Appointment List')
            form3 = RegistryForm.objects.create(name='myAppointments', sections='apptList', registry=self.registry,
                                                abbreviated_name='My Appointments')

            cfg1 = ContextFormGroup.objects.create(code='clinicalVisit', registry=self.registry, name='Clinical Visit',
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
            form4 = RegistryForm.objects.create(name='recentSymptoms', sections='symptoms', registry=self.registry,
                                                abbreviated_name='Recent Symptoms')

            cfg2 = ContextFormGroup.objects.create(code='symptoms', registry=self.registry, name='Symptoms',
                                                   context_type="M", abbreviated_name="Symptoms", sort_order=2)
            cfg2.items.create(registry_form=form4)

            # Setup for multisection & multi cde values
            CommonDataElement.objects.create(code='timeToBed', abbreviated_name='Bed Time', name="Time to Bed")
            CommonDataElement.objects.create(code='timesAwoke', abbreviated_name='Times Awoke',
                                             name="Times Awoke during the night", allow_multiple=True)
            Section.objects.create(code='sleepDiary', elements='timeToBed,timesAwoke', abbreviated_name='Sleep Diary',
                                   display_name='Sleep Diary', allow_multiple=True)
            form5 = RegistryForm.objects.create(name='sleep', sections='sleepDiary', registry=self.registry,
                                                abbreviated_name='Sleep')

            cfg3 = ContextFormGroup.objects.create(code='sleepTracking', registry=self.registry, name='Sleep Tracking',
                                                   context_type="M", abbreviated_name="Sleep Tracking", sort_order=3)
            cfg3.items.create(registry_form=form5)

            # Create clinical data
            c_type = ContentType.objects.get_for_model(patient)
            ctx1 = RDRFContext.objects.create(context_form_group=cfg1, registry=self.registry, content_type=c_type,
                                              object_id=patient.id)
            ctx2 = RDRFContext.objects.create(context_form_group=cfg2, registry=self.registry, content_type=c_type,
                                              object_id=patient.id)
            ctx3 = RDRFContext.objects.create(context_form_group=cfg2, registry=self.registry, content_type=c_type,
                                              object_id=patient.id)
            ctx4 = RDRFContext.objects.create(context_form_group=cfg3, registry=self.registry, content_type=c_type,
                                              object_id=patient.id)

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
            ClinicalData.objects.create(registry_code='test', django_id=patient.id, django_model='Patient',
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

            ClinicalData.objects.create(registry_code='test', django_id=patient.id, django_model='Patient',
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

            ClinicalData.objects.create(registry_code='test', django_id=patient.id, django_model='Patient',
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

            ClinicalData.objects.create(registry_code='test', django_id=patient.id, django_model='Patient',
                                        collection="cdes",
                                        context_id=ctx4.id, data=multisection_data)

            return create_dynamic_schema()

        p1 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1))
        p1.rdrf_registry.set([self.registry])

        schema = setup_test_registry_and_clinical_data(p1)
        client = Client(schema)

        # Fixed context
        result = client.execute("""
        {
          patients(registryCode: "test") {
            clinicalData {
              clinicalVisit {
                firstVisit {
                  inBed {
                    lieFlat
                    needHelp
                  }
                }
                myBreathing {
                  breathing {
                    breathAssist
                  }
                }
              }
            }
          }
        }
        """, context_value=self.query_context)

        self.assertEqual({
            "data": {
                "patients": [
                    {
                        "clinicalData": {
                            "clinicalVisit": {
                                "firstVisit": {
                                    "inBed": {
                                        "lieFlat": "5",
                                        "needHelp": ""
                                    }
                                },
                                "myBreathing": {
                                    "breathing": {
                                        "breathAssist": "oxygen"
                                    }
                                }
                            }
                        }
                    }
                ]
            }
        }, result)

        # Longitudinal context
        result = client.execute("""
        {
          patients(registryCode: "test") {
            clinicalData {
              symptoms {
                recentSymptoms {
                  data {
                    symptoms {
                      completedDate
                      fatigue
                      pain
                    }
                  }
                }
              }
            }
          }
        }
        """, context_value=self.query_context)

        self.assertEqual({
            "data": {
                "patients": [
                    {
                        "clinicalData": {
                            "symptoms": {
                                "recentSymptoms": [
                                    {
                                        "data": {
                                            "symptoms": {"completedDate": "2022-02-07", "fatigue": "4", "pain": "1"}
                                        }
                                    },
                                    {
                                        "data": {
                                            "symptoms": {"completedDate": "2022-02-08", "fatigue": "3", "pain": "2"}
                                        }
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }, result)

        # Mixed fixed and longitudinal context
        result = client.execute("""
        {
          patients(registryCode: "test") {
            clinicalData {
              clinicalVisit {
                firstVisit {
                  inBed {
                    lieFlat
                  }
                }
              }
              symptoms {
                recentSymptoms {
                  data {
                    symptoms {
                      completedDate
                      fatigue
                    }
                  }
                }
              }
            }
          }
        }
        """, context_value=self.query_context)

        self.assertEqual({
            "data": {
                "patients": [
                    {
                        "clinicalData": {
                            "clinicalVisit": {
                                "firstVisit": {
                                    "inBed": {
                                        "lieFlat": "5",
                                    }
                                },
                            },
                            "symptoms": {
                                "recentSymptoms": [
                                    {
                                        "data": {
                                            "symptoms": {"completedDate": "2022-02-07", "fatigue": "4"}
                                        }
                                    },
                                    {
                                        "data": {
                                            "symptoms": {"completedDate": "2022-02-08", "fatigue": "3"}
                                        }
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }, result)

        # Multisection & Multi value
        result = client.execute("""
        {
          patients(registryCode: "test") {
            clinicalData {
              sleepTracking {
                sleep {
                  data {
                    sleepDiary {
                      timeToBed
                      timesAwoke
                    }
                  }
                }
              }
            }
          }
        }
        """, context_value=self.query_context)

        self.assertEqual({
            "data": {
                "patients": [
                    {
                        "clinicalData": {
                            "sleepTracking": {
                                "sleep": [
                                    {
                                        "data": {
                                            "sleepDiary": [
                                                {"timeToBed": "9:55pm", "timesAwoke": ["1:00am", "3:00am"]},
                                                {"timeToBed": "8:45pm", "timesAwoke": ["11:45pm", "5:30am"]}
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        }, result)

import uuid

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from rdrf.models.definition.models import RegistryDashboard, Registry, ContextFormGroup, RDRFContext, RegistryForm, \
    Section, CommonDataElement, ConsentQuestion, ConsentSection, ClinicalData
from rdrf.testing.unit.tests import RDRFTestCase
from rdrf.views.dashboard_view import ParentDashboard
from registry.groups.models import CustomUser
from registry.groups import GROUPS as RDRF_GROUPS
from registry.patients.models import Patient, ParentGuardian, ConsentValue


def create_valid_patient(id=None, registry=None):
    patient = Patient.objects.create(id=id, consent=True, date_of_birth='1999-12-12')
    if registry:
        patient.rdrf_registry.set([registry])
    return patient


def list_dashboards(user):
    return list(RegistryDashboard.objects.filter_user_parent_dashboards(user).all())


class RegistryDashboardManagerTest(TestCase):
    def setUp(self):

        def create_user_with_group(group):
            user = CustomUser.objects.create(username=uuid.uuid1())
            user.add_group(group)
            return user

        # Registries
        self.registry_A = Registry.objects.create(code='A')
        self.registry_B = Registry.objects.create(code='B')
        self.registry_C = Registry.objects.create(code='C')

        # Dashboards
        self.dashboard_registry_A = RegistryDashboard.objects.create(registry=self.registry_A)
        self.dashboard_registry_B = RegistryDashboard.objects.create(registry=self.registry_B)

        # Patients
        self.patient1 = create_valid_patient()
        self.patient2 = create_valid_patient()
        self.patient3 = create_valid_patient()
        self.patient4 = create_valid_patient()

        self.patient1.rdrf_registry.set([self.registry_A])
        self.patient2.rdrf_registry.set([self.registry_A])

        self.patient3.rdrf_registry.set([self.registry_B])
        self.patient4.rdrf_registry.set([self.registry_C])

        self.parent_user = create_user_with_group(RDRF_GROUPS.PARENT)
        self.patient_user = create_user_with_group(RDRF_GROUPS.PATIENT)
        self.carer_user = create_user_with_group(RDRF_GROUPS.CARER)

    def test_get_dashboards_for_parent_user(self):
        parent = ParentGuardian.objects.create(user=self.parent_user)

        # Parent has one child, in a registry, with a dashboard.
        parent.patient.set([self.patient1])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_A])

        parent.patient.set([self.patient3])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_B])

        # Parent has one child, in a registry, with no dashboard
        parent.patient.set([self.patient4])
        self.assertEqual(list_dashboards(parent.user), [])

        # Parent has multiple children, all in one registry, with a dashboard
        parent.patient.set([self.patient1, self.patient2])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_A])

        # Parent has multiple children, in different registries, all with a dashboard
        parent.patient.set([self.patient1, self.patient3])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_A, self.dashboard_registry_B])

        # Parent has multiple children, in different registries, only one with a dashboard
        parent.patient.set([self.patient3, self.patient4])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_B])

    def test_dashboards_for_other_users(self):
        self.patient1.carer = self.carer_user
        self.assertEqual(list_dashboards(self.carer_user), [])

        self.patient1.user = self.patient_user
        self.assertEqual(list_dashboards(self.patient_user), [])


class ParentDashboardTest(RDRFTestCase):
    databases = ['default', 'clinical']
    maxDiff = None

    def setUp(self):
        self.registry = Registry.objects.create(code='TEST')
        self.dashboard = RegistryDashboard.objects.create(registry=self.registry)

    def _request(self):
        class TestContext:
            user = CustomUser.objects.get(username='admin')
        return TestContext()

    def _create_patient_context(self, patient, context_form_group, id=None):
        return RDRFContext.objects.create(id=id,
                                          registry=self.registry,
                                          context_form_group=context_form_group,
                                          object_id=patient.id,
                                          content_type=ContentType.objects.get_for_model(patient))

    def test_patient_contexts(self):
        patient = create_valid_patient()
        parent_dashboard = ParentDashboard(self._request(), self.dashboard, patient)

        self.assertEqual(parent_dashboard._load_contexts(), {})

        cfg1 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_1')
        cfg2 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_2')

        self.assertEqual(parent_dashboard._load_contexts(), {cfg1: None, cfg2: None})

        ctx1 = self._create_patient_context(patient, cfg1)

        self.assertEqual(parent_dashboard._load_contexts(), {cfg1: ctx1, cfg2: None})

        # Ensure only the latest Context for the CFG is retrieved
        ctx2 = self._create_patient_context(patient, cfg1)

        self.assertEqual(parent_dashboard._load_contexts(), {cfg1: ctx2, cfg2: None})

    def test_get_patient_context(self):
        p1 = create_valid_patient(registry=self.registry)
        p2 = create_valid_patient(registry=self.registry)

        cfg1 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_1', context_type='F')
        cfg2 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_2', context_type='M')
        cfg3 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_3', context_type='F')
        cfg4 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_4', context_type='M')

        ctx1 = self._create_patient_context(p1, cfg1)
        ctx2 = self._create_patient_context(p1, cfg2)

        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p1)

        self.assertEqual(parent_dashboard._get_patient_context(cfg1), ctx1)
        self.assertEqual(parent_dashboard._get_patient_context(cfg2), ctx2)
        self.assertEqual(parent_dashboard._get_patient_context(cfg4), None)

        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p2)
        self.assertEqual(parent_dashboard._get_patient_context(cfg3), p2.default_context(self.registry))

    def test_get_form_link(self):
        cfg1 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_1', context_type='F')
        cfg2 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_2', context_type='M')
        CommonDataElement.objects.create(code='C1', abbreviated_name='C1')
        Section.objects.create(code='S1', abbreviated_name='S1', elements='C1')
        form1 = RegistryForm.objects.create(id=31, name='form1', registry=self.registry, abbreviated_name='form1', sections='S1')
        form2 = RegistryForm.objects.create(id=32, name='form2', registry=self.registry, abbreviated_name='form2', sections='S1')
        cfg1.items.create(registry_form=form1)
        cfg2.items.create(registry_form=form2)

        p1 = create_valid_patient(id=11, registry=self.registry)
        ctx1 = self._create_patient_context(p1, cfg1, id=1)
        self._create_patient_context(p1, cfg2, id=2)

        p2 = create_valid_patient(id=12, registry=self.registry)

        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p1)
        self.assertEqual(parent_dashboard._get_form_link(cfg1, form1), '/TEST/forms/31/11/1')
        self.assertEqual(parent_dashboard._get_form_link(cfg1, form1, ctx1), '/TEST/forms/31/11/1')
        self.assertEqual(parent_dashboard._get_form_link(cfg2, form2), '/TEST/forms/32/11/2')

        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p2)
        context = p2.default_context(self.registry)
        self.assertEqual(parent_dashboard._get_form_link(cfg1, form1), f'/TEST/forms/31/12/{context.id}')
        self.assertEqual(parent_dashboard._get_form_link(cfg2, form2), '/TEST/forms/32/12/add')

    def test_patient_consent_summary(self):
        sec1 = ConsentSection.objects.create(registry=self.registry,
                                             section_label='Section 1',
                                             code='S1',
                                             validation_rule='cq1 and cq3')
        cq1 = ConsentQuestion.objects.create(section=sec1, code='cq1')
        cq2 = ConsentQuestion.objects.create(section=sec1, code='cq2')
        cq3 = ConsentQuestion.objects.create(section=sec1, code='cq3')
        cq4 = ConsentQuestion.objects.create(section=sec1, code='cq4')

        p1 = create_valid_patient()
        p2 = create_valid_patient()

        ConsentValue.objects.create(patient=p1, consent_question=cq1, answer=True)
        ConsentValue.objects.create(patient=p1, consent_question=cq2, answer=True)
        ConsentValue.objects.create(patient=p1, consent_question=cq3, answer=True)

        ConsentValue.objects.create(patient=p2, consent_question=cq1, answer=True)
        ConsentValue.objects.create(patient=p2, consent_question=cq4, answer=False)  # TRRF considers this as valid

        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p1)
        self.assertEqual(parent_dashboard._patient_consent_summary(), {'valid': True, 'completed': 3, 'total': 4})

        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p2)
        self.assertEqual(parent_dashboard._patient_consent_summary(), {'valid': False, 'completed': 2, 'total': 4})

    def test_get_module_progress(self):
        cfg1 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_1', context_type='F', sort_order=1)
        cfg2 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_2', context_type='M', sort_order=2)
        cfg3 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_3', context_type='M', sort_order=3)
        cde1 = CommonDataElement.objects.create(code='C1', abbreviated_name='C1')
        Section.objects.create(code='S1', abbreviated_name='S1', elements='C1')
        form1 = RegistryForm.objects.create(id=61, name='form1', registry=self.registry, abbreviated_name='form1', sections='S1', position=1)
        form2 = RegistryForm.objects.create(id=62, name='form2', registry=self.registry, abbreviated_name='form2', sections='S1', position=2)
        form3 = RegistryForm.objects.create(id=63, name='form3', registry=self.registry, abbreviated_name='form3', sections='S1', position=3)
        form4 = RegistryForm.objects.create(id=64, name='form4', registry=self.registry, abbreviated_name='form4', sections='S1', position=1)
        form5 = RegistryForm.objects.create(id=65, name='form5', registry=self.registry, abbreviated_name='form5', sections='S1', position=1)

        cfg1.items.create(registry_form=form1)
        cfg1.items.create(registry_form=form2)
        cfg1.items.create(registry_form=form3)
        cfg2.items.create(registry_form=form4)
        cfg3.items.create(registry_form=form5)

        form1.complete_form_cdes.set([cde1])
        form3.complete_form_cdes.set([cde1])

        p1 = create_valid_patient(id=9, registry=self.registry)
        ctx1 = self._create_patient_context(p1, cfg1, id=7)
        ClinicalData.objects.create(registry_code='TEST', django_id=p1.id, django_model='Patient',
                                    collection="progress", context_id=ctx1.id,
                                    data={"form1_form_progress": {'percentage': 20}})

        ctx2 = self._create_patient_context(p1, cfg3, id=8)
        data = {"form5_timestamp": "2022-08-26 07:49:53.841787"}
        ClinicalData.objects.create(registry_code='TEST', django_id=p1.id, django_model='Patient',
                                    collection="cdes", context_id=ctx2.id, data=data)

        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p1)
        self.assertDictEqual(parent_dashboard._get_module_progress(),
                             {
                                 'fixed': {
                                     cfg1: {
                                         form1: {
                                             'link': '/TEST/forms/61/9/7',
                                             'progress': 20
                                         },
                                         form3: {
                                             'link': '/TEST/forms/63/9/7',
                                             'progress': 0
                                         }
                                     },
                                 },
                                 'multi': {
                                     cfg3: {
                                         form5: {
                                             'link': '/TEST/forms/65/9/add',
                                             'last_completed': '26-08-2022'
                                         }
                                     },
                                     cfg2: {
                                         form4: {
                                             'link': '/TEST/forms/64/9/add',
                                             'last_completed': None
                                         }
                                     }
                                 }
                              })

    def test_get_cde_data(self):
        cfg1 = ContextFormGroup.objects.create(registry=self.registry, code='CFG_1', context_type='F')
        cde1 = CommonDataElement.objects.create(code='C1', abbreviated_name='C1')
        sec1 = Section.objects.create(code='S1', abbreviated_name='S1', elements='C1')
        form1 = RegistryForm.objects.create(id=61, name='form1', registry=self.registry, abbreviated_name='form1', sections='S1')

        p1 = create_valid_patient(id=9, registry=self.registry)
        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p1)

        # Returns None if patient has no context
        self.assertEqual(parent_dashboard._get_cde_data(cfg1, form1, sec1, cde1), None)

        ctx1 = self._create_patient_context(p1, cfg1, id=8)

        # Returns None if patient has no matching data
        parent_dashboard._contexts = parent_dashboard._load_contexts()
        self.assertEqual(parent_dashboard._get_cde_data(cfg1, form1, sec1, cde1), None)

        data = {"forms": [{"name": "form1", "sections": [{"code": "S1", "allow_multiple": False, "cdes": [{"code": "C1", "value": "Patient Response ABC"}]}]}]}
        ClinicalData.objects.create(registry_code='TEST', django_id=p1.id, django_model='Patient',
                                    collection="cdes", context_id=ctx1.id, data=data)
        self.assertEqual(parent_dashboard._get_cde_data(cfg1, form1, sec1, cde1), "Patient Response ABC")

    def test_get_demographic_data(self):
        demographics_widget = self.dashboard.widgets.create(widget_type='Demographics')
        demographics_widget.demographics.create(label='Given Name', model='patient', field='givenNames', sort_order=1)
        demographics_widget.demographics.create(label='Birth Country', model='patient', field='countryOfBirth', sort_order=2)
        demographics_widget.demographics.create(label='Mobile Phone No', model='patient', field='mobilePhone', sort_order=4)
        demographics_widget.demographics.create(label='Home Phone No', model='patient', field='homePhone', sort_order=3)

        p1 = create_valid_patient(registry=self.registry)
        p1.country_of_birth = 'AU'
        p1.given_names = 'Kylie-Anne'
        p1.mobile_phone = '+61412123456'
        p1.save()
        parent_dashboard = ParentDashboard(self._request(), self.dashboard, p1)

        self.assertDictEqual(parent_dashboard._get_demographic_data(demographics_widget),
                             {'givenNames': {'label': 'Given Name', 'value': 'Kylie-Anne'},
                              'countryOfBirth': {'label': 'Birth Country', 'value': 'AU'},
                              'homePhone': {'label': 'Home Phone No', 'value': None},
                              'mobilePhone': {'label': 'Mobile Phone No', 'value': '+61412123456'},
                              })

import logging
import re
from datetime import datetime

from rdrf.models.definition.models import Registry
from rdrf.patients.query_data import build_facet_query, build_all_patients_query, \
    build_patients_query, query_all_patients, query_patient_facets
from rdrf.testing.unit.tests import RDRFTestCase
from registry.groups.models import CustomUser
from registry.patients.models import Patient, LivingStates


class PatientQueryDataTest(RDRFTestCase):

    def _request(self):
        class TestContext:
            user = CustomUser.objects.get(username='admin')
        return TestContext()

    def _query_syntax(self, query_string):
        return re.sub(r'\s+', ' ', query_string.strip())

    def _create_patient(self,
                        registry,
                        date_of_birth=datetime(1978, 6, 15),
                        living_state=LivingStates.ALIVE,
                        given_names=None,
                        family_name=None):
        p = Patient.objects.create(consent=True,
                                   given_names=given_names,
                                   family_name=family_name,
                                   date_of_birth=date_of_birth,
                                   living_status=living_state)
        p.rdrf_registry.set([registry])
        p.save()
        return p

    def test_facet_query(self):
        facet_query = build_facet_query()
        query = build_all_patients_query([facet_query], {'registryCode': '"fh"'})

        expected_facet_query = '''
            query {
                allPatients(registryCode: "fh") {
                    facets {
                        field
                        categories {
                            label
                            value
                            total
                        }
                    }
                }
            }
        '''

        self.assertEqual(self._query_syntax(expected_facet_query), query)

    def test_get_facets(self):
        registry = Registry.objects.get(code='fh')
        self._create_patient(registry, living_state=LivingStates.ALIVE)
        self._create_patient(registry, living_state=LivingStates.DECEASED)

        facets = query_patient_facets(self._request(), registry, ['living_status'])
        self.assertEqual(['living_status'], [facet.get('field') for facet in facets])

    def test_build_patients_query(self):
        query = build_patients_query(['givenNames', 'familyName'], ['-date_of_birth'], {'offset': 0, 'limit': 5})
        expected_query = """
            patients(sort: ["-date_of_birth"], offset: 0, limit: 5) {
                givenNames
                familyName
            }
        """
        self.assertEqual(self._query_syntax(expected_query), query)

    def test_get_all_patients_minimal_data(self):
        registry = Registry.objects.get(code='fh')
        p1 = self._create_patient(registry, living_state=LivingStates.ALIVE)
        p2 = self._create_patient(registry, living_state=LivingStates.ALIVE)
        p3 = self._create_patient(registry, living_state=LivingStates.ALIVE)
        p4 = self._create_patient(registry, living_state=LivingStates.DECEASED)

        filters = {}
        patient_fields = ['id', 'livingStatus']
        sort_fields = []
        pagination = {}

        all_patients = query_all_patients(self._request(), registry, filters, patient_fields, sort_fields, pagination)

        expected_patients = [{str(p1.id): 'ALIVE'}, {str(p2.id): 'ALIVE'}, {str(p3.id): 'ALIVE'}, {str(p4.id): 'DECEASED'}]
        self.assertEqual(expected_patients,
                         [{p['id']: p['livingStatus']} for p in (all_patients.get('patients'))])

    def test_get_all_patients_sort_and_pagination(self):
        def expected_patients(patients):
            return [str(patient.id) for patient in patients]
        registry = Registry.objects.get(code='fh')

        p1 = self._create_patient(registry, date_of_birth=datetime(1988, 6, 10), living_state=LivingStates.ALIVE)
        p2 = self._create_patient(registry, date_of_birth=datetime(1992, 1, 27), living_state=LivingStates.ALIVE)
        p3 = self._create_patient(registry, date_of_birth=datetime(1971, 3, 12), living_state=LivingStates.ALIVE)
        p4 = self._create_patient(registry, date_of_birth=datetime(1989, 11, 1), living_state=LivingStates.DECEASED)

        filters = {}
        patient_fields = ['id']
        sort_fields = ['-date_of_birth']
        pagination = {}

        all_patients = query_all_patients(self._request(), registry, filters, patient_fields, sort_fields, pagination)

        self.assertEqual(expected_patients([p2, p4, p1, p3]),
                         [p['id'] for p in (all_patients.get('patients'))])

        pagination = {'offset': 2, 'limit': 2}
        all_patients = query_all_patients(self._request(), registry, filters, patient_fields, sort_fields, pagination)

        self.assertEqual(expected_patients([p1, p3]),
                         [p['id'] for p in (all_patients.get('patients'))])

    def test_get_all_patients_search_and_filter(self):
        registry = Registry.objects.get(code='fh')
        self._create_patient(registry, given_names='Jane', family_name='Brown')
        self._create_patient(registry, given_names='Oliver', family_name='Grey')
        self._create_patient(registry, given_names='Grace', family_name='Oliver')

        filters = {'search_term': 'Oliver'}
        patient_fields = ['id', 'givenNames', 'familyName']

        all_patients = query_all_patients(self._request(), registry, filters, patient_fields, [], {})
        logging.getLogger(__name__).info(f'results={all_patients}')

        self.assertEqual(['GREY, Oliver', 'OLIVER, Grace'],
                         [f'{p.get("familyName")}, {p.get("givenNames")}' for p in all_patients.get('patients')])

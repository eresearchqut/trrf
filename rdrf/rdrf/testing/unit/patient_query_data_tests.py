import re
from datetime import datetime

from rdrf.models.definition.models import Registry
from rdrf.patients.query_data import build_facet_query, build_all_patients_query, \
    build_patients_query, query_patient_facets, query_patient
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
        registry = Registry.objects.get(code='fh')
        facet_query = build_facet_query(['livingStatus', 'workingGroups'])
        query = build_all_patients_query(registry, [facet_query])

        expected_facet_query = '''
            query {
                fh {
                    allPatients {
                        facets {
                            livingStatus {
                                label
                                value
                                total
                            }
                            workingGroups {
                                label
                                value
                                total
                            }
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

        facets = query_patient_facets(self._request(), registry, ['livingStatus'])
        self.assertEqual(['livingStatus'], list(facets.keys()))

    def test_build_patients_query(self):
        query = build_patients_query(['givenNames', 'familyName'], ['-date_of_birth'], {'offset': 0, 'limit': 5})
        expected_query = """
            patients(sort: ["-date_of_birth"], offset: 0, limit: 5) {
                givenNames
                familyName
            }
        """
        self.assertEqual(self._query_syntax(expected_query), query)

    def test_query_patient(self):
        registry = Registry.objects.get(code='fh')
        p1 = self._create_patient(registry, given_names='Kyle', family_name='Botany')
        p2 = self._create_patient(registry, given_names='Jamie', family_name='Grey')
        fields = ['givenNames', 'familyName']

        patient = query_patient(self._request(), registry, p2.id, fields)
        self.assertEqual(patient.get('givenNames'), 'Jamie')
        self.assertEqual(patient.get('familyName'), 'GREY')

        patient = query_patient(self._request(), registry, p1.id, fields)
        self.assertEqual(patient.get('givenNames'), 'Kyle')
        self.assertEqual(patient.get('familyName'), 'BOTANY')

import re
from datetime import datetime

from rdrf.models.definition.models import Registry
from rdrf.patients.query_data import build_facet_query, build_all_patients_query, \
    build_patients_query, query_patient_facets, query_patient
from rdrf.testing.unit.tests import RDRFTestCase
from registry.groups.models import CustomUser, WorkingGroup
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
                        working_groups=None,
                        given_names=None,
                        family_name=None):
        p = Patient.objects.create(consent=True,
                                   given_names=given_names,
                                   family_name=family_name,
                                   date_of_birth=date_of_birth,
                                   living_status=living_state)
        p.rdrf_registry.set([registry])

        if working_groups:
            p.working_groups.set([wg.id for wg in working_groups])

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

    def test_get_facets_with_filter(self):
        registry = Registry.objects.get(code='fh')

        qld = WorkingGroup.objects.create(name="QLD")
        vic = WorkingGroup.objects.create(name="VIC")
        nsw = WorkingGroup.objects.create(name="NSW")

        self._create_patient(registry, living_state=LivingStates.ALIVE, working_groups=[qld])
        self._create_patient(registry, living_state=LivingStates.ALIVE, working_groups=[qld, nsw])
        self._create_patient(registry, living_state=LivingStates.ALIVE, working_groups=[nsw])
        self._create_patient(registry, living_state=LivingStates.ALIVE, working_groups=[nsw])
        self._create_patient(registry, living_state=LivingStates.ALIVE, working_groups=[vic, nsw])
        self._create_patient(registry, living_state=LivingStates.DECEASED, working_groups=[vic])
        self._create_patient(registry, living_state=LivingStates.DECEASED, working_groups=[vic])
        self._create_patient(registry, living_state=LivingStates.DECEASED, working_groups=[nsw])
        self._create_patient(registry, living_state=LivingStates.DECEASED, working_groups=[qld])

        facets = query_patient_facets(self._request(), registry, ['workingGroups'], filters={"livingStatus": LivingStates.ALIVE})
        self.assertEqual({"workingGroups": [
            {"label": "QLD", "total": 2, "value": str(qld.id)},
            {"label": "VIC", "total": 1, "value": str(vic.id)},
            {"label": "NSW", "total": 4, "value": str(nsw.id)}
        ]}, facets)

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

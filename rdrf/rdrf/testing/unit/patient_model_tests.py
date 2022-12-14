import logging
from datetime import date, datetime
from unittest import mock
from unittest.mock import Mock

import pytest

from rdrf.models.definition.models import Registry
from rdrf.testing.unit.tests import RDRFTestCase
from registry.patients import models
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


class PatientAgeTest(RDRFTestCase):

    def setUp(self):
        registry = Registry.objects.create()
        self.patient = self._create_patient(registry, date(2000, 1, 1))

    def _create_patient(self,
                        registry,
                        date_of_birth):
        p = Patient.objects.create(consent=True,
                                   date_of_birth=date_of_birth)
        p.rdrf_registry.set([registry])
        p.save()
        return p

    def _get_calculated_age(self, patient, date_of_birth, date_of_death=None):
        patient.date_of_birth = date_of_birth
        patient.date_of_death = date_of_death
        return patient.age

    @mock.patch(f'{models.__name__}.datetime', wraps=datetime)
    def test_living_patient_age(self, *args, **kwargs):

        models.datetime.date.today = Mock(return_value=date(2022, 12, 1))

        self.assertEqual(self._get_calculated_age(self.patient, date(2000, 1, 1)), 22)
        self.assertEqual(self._get_calculated_age(self.patient, date(2019, 1, 1)), 3)
        self.assertEqual(self._get_calculated_age(self.patient, date(2019, 12, 2)), 2)  # birthday month/day greater than today
        self.assertEqual(self._get_calculated_age(self.patient, date(2020, 2, 29)), 2)  # Valid leap year, "current" year (2022) is not a leap year.

        with pytest.raises(ValueError):
            self.assertEqual(self._get_calculated_age(self.patient, date(2017, 2, 29)), 5)  # Invalid leap year

    @mock.patch(f'{models.__name__}.datetime', wraps=datetime)
    def test_deceased_patient_age(self, *args, **kwargs):

        models.datetime.date.today = Mock(return_value=date(2021, 6, 15))

        self.assertEqual(self._get_calculated_age(self.patient, date_of_birth=date(2000, 1, 1), date_of_death=date(2010, 6, 3)), 10)
        self.assertEqual(self._get_calculated_age(self.patient, date_of_birth=date(2019, 1, 1), date_of_death=date(2019, 6, 3)), 0)
        self.assertEqual(self._get_calculated_age(self.patient, date_of_birth=date(1970, 12, 2), date_of_death=date(1999, 7, 24)), 28)  # birthday month/day greater than DOD
        self.assertEqual(self._get_calculated_age(self.patient, date_of_birth=date(2000, 2, 29), date_of_death=date(2005, 5, 24)), 5)  # Valid leap year, DOD year is not a leap year.
        self.assertEqual(self._get_calculated_age(self.patient, date_of_birth=date(2000, 2, 29), date_of_death=date(2008, 5, 24)), 8)  # Valid leap year, DOD year is a leap year.

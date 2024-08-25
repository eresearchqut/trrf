import json

from django.test import TestCase

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry
from report.report_configuration import get_configuration


class ReportGeneratorTestCase(TestCase):
    maxDiff = None

    def test_get_configuration_patient_guid_feature(self):
        reg1 = Registry.objects.create(code="REG1")
        reg2 = Registry.objects.create(code="REG2")

        key_patient_guid = "patientguid {guid}"
        patient_fields = (
            lambda: get_configuration()
            .get("demographic_model", {})
            .get("patient", {})
            .get("fields", {})
        )

        self.assertFalse(key_patient_guid in patient_fields().keys())

        # Switch on the patient guid feature for one of the registries
        reg2.metadata_json = json.dumps(
            {"features": [RegistryFeatures.PATIENT_GUID]}
        )
        reg2.save()

        self.assertTrue(key_patient_guid in patient_fields().keys())

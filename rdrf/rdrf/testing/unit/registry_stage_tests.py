import yaml

from rdrf.models.definition.models import Registry
from rdrf.services.io.defs.exporter import Exporter
from rdrf.services.io.defs.importer import Importer, ImportState, RegistryImportError

from registry.patients.models import Patient, PatientStage, PatientStageRule

from .tests import RDRFTestCase


class RegistryStageTests(RDRFTestCase):

    def setUp(self):
        self.registry = Registry.objects.get(code='reg3')
        self.exported_file = "/tmp/test.yaml"
        return super().setUp()

    def test_stage_and_rule_creation_on_feature_add(self):
        self.registry.metadata_json = "{\"features\":[\"stages\"]}"
        self.registry.save()
        self.assertTrue(PatientStage.objects.filter(registry=self.registry).exists())
        self.assertEqual(PatientStage.objects.filter(registry=self.registry).count(), 7)
        self.assertIsNotNone(PatientStage.objects.filter(registry=self.registry, name='Trial').first())
        self.assertTrue(PatientStageRule.objects.filter(registry=self.registry).exists())
        self.assertEqual(PatientStageRule.objects.filter(registry=self.registry).count(), 2)

    def _export(self):
        self.registry.metadata_json = "{\"features\":[\"stages\"]}"
        self.registry.save()
        self.exporter = Exporter(self.registry)
        yaml_data, errors = self.exporter.export_yaml()
        self.assertTrue(isinstance(errors, list), "Expected errors list in exporter export_yaml")
        self.assertEqual(len(errors), 0, "Expected zero errors instead got:%s" % errors)
        self.assertTrue(isinstance(yaml_data, str), "Expected yaml_data is  string:%s" % type(yaml_data))
        with open(self.exported_file, "w") as f:
            f.write(yaml_data)

    def _check_yaml(self):
        with open(self.exported_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            self.assertTrue("patient_stages" in data)
            self.assertTrue("patient_stage_rules" in data)
            self.assertEqual(len(data["patient_stages"]), 7)
            self.assertEqual(len(data["patient_stage_rules"]), 2)

    def test_stage_import_export_delete_stage(self):
        self._export()
        self._check_yaml()

        PatientStage.objects.create(name="New test stage", registry=self.registry)

        existing_stage_ids = set(PatientStage.objects.filter(registry=self.registry).values_list('pk', flat=True))
        existing_rule_ids = set(PatientStageRule.objects.filter(registry=self.registry).values_list('pk', flat=True))
        importer = Importer()
        importer.load_yaml(self.exported_file)
        importer.create_registry()
        self.assertEqual(importer.state, ImportState.SOUND)
        stage_ids = set(PatientStage.objects.filter(registry=self.registry).values_list('pk', flat=True))
        rule_ids = set(PatientStageRule.objects.filter(registry=self.registry).values_list('pk', flat=True))
        self.assertNotEqual(existing_stage_ids, stage_ids)
        self.assertNotEqual(existing_rule_ids, rule_ids)
        self.assertFalse(PatientStage.objects.filter(name="New test stage", registry=self.registry).exists())

    def test_stage_import_export_associated_patient(self):
        self._export()
        self._check_yaml()
        new_stage = PatientStage.objects.create(name="New test stage", registry=self.registry)
        p = Patient.objects.create(
            family_name="John",
            given_names="Doe",
            consent=True,
            date_of_birth="2000-01-01",
            stage=new_stage
        )
        p.rdrf_registry.add(self.registry)

        importer = Importer()
        importer.load_yaml(self.exported_file)
        with self.assertRaises(RegistryImportError) as e:
            importer.create_registry()
        self.assertEqual(
            str(e.exception),
            "Cannot remove ['New test stage'] stages as there are patients associated with them !"
        )

    def test_stage_import_export_rename_stage(self):
        self._export()
        self._check_yaml()

        PatientStage.objects.filter(name="Trial", registry=self.registry).update(name="Trial2")

        importer = Importer()
        importer.load_yaml(self.exported_file)
        importer.create_registry()
        self.assertEqual(importer.state, ImportState.SOUND)
        self.assertFalse(PatientStage.objects.filter(name="Trial2", registry=self.registry).exists())
        self.assertTrue(PatientStage.objects.filter(name="Trial", registry=self.registry).exists())

    def test_stage_import_export_delete_next_prev_stages(self):
        self._export()
        self._check_yaml()

        stage = PatientStage.objects.filter(name="Trial", registry=self.registry).first()
        prev_stages_count = stage.allowed_prev_stages.count()
        next_stages_count = stage.allowed_next_stages.count()
        stage.allowed_prev_stages.clear()
        stage.allowed_next_stages.clear()

        importer = Importer()
        importer.load_yaml(self.exported_file)
        importer.create_registry()
        self.assertEqual(importer.state, ImportState.SOUND)
        stage = PatientStage.objects.filter(name="Trial", registry=self.registry).first()
        self.assertEqual(stage.allowed_next_stages.count(), next_stages_count)
        self.assertEqual(stage.allowed_prev_stages.count(), prev_stages_count)

    def test_stage_import_export_add_stage(self):
        self._export()
        self._check_yaml()

        PatientStage.objects.filter(name="Trial", registry=self.registry).delete()

        importer = Importer()
        importer.load_yaml(self.exported_file)
        importer.create_registry()
        self.assertEqual(importer.state, ImportState.SOUND)
        stage = PatientStage.objects.filter(name="Trial", registry=self.registry).first()
        self.assertIsNotNone(stage)

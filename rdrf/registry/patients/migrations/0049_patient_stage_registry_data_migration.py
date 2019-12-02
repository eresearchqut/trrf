# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.db import migrations, models
from rdrf.helpers.registry_features import RegistryFeatures


def has_stages_feature(registry):
    metadata = {}
    if registry.metadata_json:
        try:
            metadata = json.loads(registry.metadata_json)
        except Exception:
            pass
    if "features" in metadata:
        return RegistryFeatures.STAGES in metadata["features"]
    else:
        return False


def set_registry_for_patient_stages(apps, schema_editor):
    PatientStage = apps.get_model('patients', 'PatientStage')
    PatientStageRule = apps.get_model('patients', 'PatientStageRule')
    Registry = apps.get_model('rdrf', 'Registry')
    Patient = apps.get_model('patients', 'Patient')

    registry_stages_dict = {}
    stages_to_migrate_qs = PatientStage.objects.filter(registry__isnull=True)
    for reg in Registry.objects.all():
        if has_stages_feature(reg):
            new_stages_dict = {}
            for stage in stages_to_migrate_qs:
                new_stage = PatientStage.objects.create(
                    name=stage.name,
                    registry=reg
                )
                new_stages_dict[stage.id] = new_stage
            for stage in stages_to_migrate_qs:
                new_stage = new_stages_dict[stage.id]
                for next_stage in stage.allowed_next_stages.all():
                    new_stage.allowed_next_stages.add(new_stages_dict[next_stage.id])
                for prev_stage in stage.allowed_prev_stages.all():
                    new_stage.allowed_prev_stages.add(new_stages_dict[prev_stage.id])
            registry_stages_dict[reg.id] = new_stages_dict
    
    for patient in Patient.objects.exclude(stage__isnull=True):
        registry_model = patient.rdrf_registry.first()
        if registry_model.id in registry_stages_dict:
            new_stages_dict = registry_stages_dict[registry_model.id]
            patient.stage = new_stages_dict[patient.stage.id]
            patient.save()
    
    for rule in PatientStageRule.objects.all():
        if rule.registry and rule.registry.id in registry_stages_dict:
            new_stages_dict = registry_stages_dict[rule.registry.id]
            modified = False
            if rule.from_stage:
                rule.from_stage = new_stages_dict[rule.from_stage.id]
                modified = True
            if rule.to_stage:
                rule.to_stage = new_stages_dict[rule.to_stage.id]
                modified = True
            if modified:
                rule.save()

    stages_to_migrate_qs.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0048_patientstage_registry'),
    ]

    operations = [
        migrations.RunPython(set_registry_for_patient_stages, migrations.RunPython.noop)
    ]

from django.core.management.base import BaseCommand
from rdrf.models.definition.models import Registry, CDEFile, ClinicalData
from registry.patients.models import Patient

import sys


class Command(BaseCommand):
    help = "Fixes CDEFile records which don't have patient or uploaded_by fields set"

    def add_arguments(self, parser):
        parser.add_argument("registry_code")

    def handle(self, registry_code, **options):
        self.registry_model = None
        try:
            self.registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self.stderr.write("Error: Unknown registry code: %s" %
                              registry_code)
            sys.exit(1)
            return

        if self.registry_model is not None:
            self._fix_entries()
            self.stdout.write("Done")

    def _entry_exists(self, cd_models, form, section, cde):
        for cd in cd_models:
            d = cd['data']
            for f in d['forms']:
                if f['name'] == form:
                    for s in f['sections']:
                        if s['code'] == section:
                            for c in s['cdes']:
                                if isinstance(c, list):
                                    for idx in range(len(c)):
                                        if c[idx]['code'] == cde:
                                            return cd['django_id']
                                else:
                                    if c['code'] == cde:
                                        return cd['django_id']
        return None

    def _fix_entries(self):
        reg_code = self.registry_model.code
        cd_models = list(
            ClinicalData.objects.filter(
                registry_code=reg_code, django_model='Patient', collection='cdes'
            ).order_by('-id').values('django_id', 'data')
        )
        to_fix_qs = CDEFile.objects.filter(registry_code=reg_code, patient__isnull=True)
        self.stdout.write(f"Found {to_fix_qs.count()} entries to fix")
        updated = 0
        for cdefile in to_fix_qs:
            patient_id = self._entry_exists(cd_models, cdefile.form_name, cdefile.section_code, cdefile.cde_code)
            patient = Patient.objects.filter(pk=patient_id).first()
            if patient:
                cdefile.patient = patient
                cdefile.uploaded_by = patient.user
                cdefile.save()
                updated += 1
            else:
                self.stdout.write(f"Can't find patient with id {patient_id}")
        self.stdout.write(f"Updated {updated} records")

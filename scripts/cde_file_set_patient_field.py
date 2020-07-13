# -*- coding: utf-8 -*-
import django
import logging

from rdrf.models.definition.models import CDEFile, ClinicalData
from registry.patients.models import Patient
from rdrf.db import filestorage

django.setup()

logger = logging.getLogger(__name__)


def entry_exists(cd_models, form, section, cde, file_id):
    def get_section():
        for cd_model in cd_models:
            d = cd_model.get('data', {})
            for f in d.get('forms', []):
                if f['name'] == form:
                    for s in f['sections']:
                        if s['code'] == section:
                            yield cd_model, s

    def cde_and_file_id_check(current):
        if not current:
            return False
        value = current.get('value', {}) or {}
        return current['code'] == cde and filestorage.get_id(value) == file_id

    for cd, form_section in get_section():
        for c in form_section['cdes']:
            if isinstance(c, list):
                if any(cde_and_file_id_check(current) for current in c):
                    return cd['django_id']
            elif cde_and_file_id_check(c):
                return cd['django_id']
    return None


def main():
    cde_files = CDEFile.objects.all()

    for cde_file in cde_files:
        query_params = {
            'collection': 'cdes',
            'django_model': 'Patient'
        }
        cde_models = list(ClinicalData.objects.filter(**query_params).order_by('-id').values('django_id', 'data'))
        patient_id = entry_exists(cde_models, cde_file.form_name, cde_file.section_code, cde_file.cde_code, cde_file.id)
        patient = Patient.objects.filter(pk=patient_id).first()

        if patient:
            logger.info(f"Set patient to {patient} for cde with id {cde_file.id}")
            cde_file.patient = patient
            cde_file.save()
        else:
            logger.info(f"Could not determine patient for cde with id {cde_file.id}")


if __name__ == '__main__':
    main()

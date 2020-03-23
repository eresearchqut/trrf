# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from django.db import migrations, models


def set_form_pk(apps, schema_editor):
    Query = apps.get_model('explorer','Query')
    RegistryForm = apps.get_model('rdrf','RegistryForm')
    forms_mapping = {
        (f.name, f.registry.code): f.id for f in RegistryForm.objects.all()
    }
    for q in Query.objects.filter(projection__isnull=False):
        try:
            proj = json.loads(q.projection)
            pk_set = False
            for cde_dict in proj:
                key = (cde_dict["formName"], cde_dict["registryCode"])
                if key in forms_mapping:
                    cde_dict["formPK"] = forms_mapping[key]
                    pk_set = True
            if pk_set:
                q.projection = proj
                q.save()
        except Exception as e:
            print(f"Error processing projection field for query with id {q.id}: {str(e)}")
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0010_fieldvalue_raw_boolean'),
    ]

    operations = [
        migrations.RunPython(
            set_form_pk, migrations.RunPython.noop
        )
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.db import migrations, models



def migrate_to_consent_configuration(apps, schema_editor):
    Registry = apps.get_model('rdrf', 'Registry')
    ConsentConfiguration = apps.get_model('rdrf', 'ConsentConfiguration')
    for reg in Registry.objects.all():
        meta_data = json.loads(reg.metadata_json) if reg.metadata_json else {}
        if 'features' in meta_data and 'consent_lock' in meta_data['features']:
            config, __ = ConsentConfiguration.objects.get_or_create(registry=reg)
            config.consent_locked = True
            config.save()
            meta_data['features'].remove('consent_lock')
            reg.metadata_json = json.dumps(meta_data)
            reg.save()


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0107_consentconfiguration'),
    ]

    operations = [
        migrations.RunPython(migrate_to_consent_configuration, migrations.RunPython.noop)
    ]

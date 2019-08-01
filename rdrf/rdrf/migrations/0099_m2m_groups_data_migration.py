# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
from django.db import migrations, models


def migrate_groups(apps, schema_editor):
    DemographicFields = apps.get_model('rdrf', 'demographicfields')
    Group = apps.get_model('auth', 'group')
    groups = defaultdict(list)
    for entry in DemographicFields.objects.all():
        groups[(entry.field, entry.readonly, entry.hidden, entry.registry_id, entry.is_section)].append(entry.group)
    DemographicFields.objects.all().delete()
    for key, value in groups.items():
        df = DemographicFields.objects.create(
            field=key[0],
            readonly=key[1],
            hidden=key[2],
            registry_id=key[3],
            is_section=key[4],
            group=value[0]
        )
        df.groups.add(*value)


def revert_groups(apps, schema_editor):
    DemographicFields = apps.get_model('rdrf', 'demographicfields')
    groups = defaultdict(list)
    for entry in DemographicFields.objects.all():
        for g in entry.groups.all():
            key = (entry.field, entry.readonly, entry.hidden, entry.registry_id, entry.is_section)
            groups[key].append(g)
        entry.groups.clear()
    DemographicFields.objects.all().delete()
    for key, value in groups.items():
        for group in value:
            DemographicFields.objects.create(
                field=key[0],
                readonly=key[1],
                hidden=key[2],
                registry_id=key[3],
                is_section=key[4],
                group=group
            )


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0098_demographic_fields_m2m_group'),
    ]

    operations = [
        migrations.RunPython(migrate_groups, revert_groups)
    ]

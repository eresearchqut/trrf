from django.core.checks import Error, register, Tags
from rdrf.services.io.defs import migrations_list
from django.db.migrations.recorder import MigrationRecorder
from django.db import connection


@register(Tags.models, deploy=True)
def import_export_logic_updates_check(app_configs, **kwargs):
    existing_migrations = migrations_list.MIGRATIONS_LIST
    all_migrations = MigrationRecorder(connection).applied_migrations()
    new_migrations = []
    for (app, name) in all_migrations.keys():
        if app in existing_migrations and name not in existing_migrations[app]:
            new_migrations.append((app, name))

    return [
        Error(
            f"New migration {name} for {app} has not been added to migrations list",
            hint="Read the instructions in docs/import-export-logic-updates.md",
            id='trrf.E002',
        ) for (app, name) in new_migrations
    ]

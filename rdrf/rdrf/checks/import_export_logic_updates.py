from django.core.checks import Error, register, Tags
from rdrf.services.io.defs.migrations_considered_for_import_export import MIGRATIONS_CONSIDERED_FOR_IMPORT_EXPORT
from django.db.migrations.recorder import MigrationRecorder
from django.db import connection


@register(Tags.models, deploy=True)
def import_export_logic_updates_check(app_configs, **kwargs):
    all_migrations = MigrationRecorder(connection).applied_migrations()
    new_migrations = []
    for (app, name) in all_migrations.keys():
        if app in MIGRATIONS_CONSIDERED_FOR_IMPORT_EXPORT and name not in MIGRATIONS_CONSIDERED_FOR_IMPORT_EXPORT[app]:
            new_migrations.append((app, name))

    return [
        Error(
            f"New migration {name} for {app} has not been added to the migrations list considered for import and export",
            hint="Read the instructions in docs/import-export-logic-updates.md",
            id='trrf.E002',
        ) for (app, name) in new_migrations
    ]

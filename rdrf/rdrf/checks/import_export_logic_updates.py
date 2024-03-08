from django.core.checks import Error, register, Tags
from rdrf.services.io.defs import migrations_list
from django.db.migrations.recorder import MigrationRecorder


@register(Tags.models, deploy=True)
def import_export_logic_updates_check(app_configs, **kwargs):
    existing_migrations = migrations_list.MIGRATIONS_LIST
    all_migrations = [(m.app, m.name) for m in MigrationRecorder.Migration.objects.filter(app__in=migrations_list.MIGRATIONS_LIST.keys())]
    new_migrations = []
    for migration in all_migrations:
        if migration[1] not in existing_migrations[migration[0]]:
            new_migrations.append(migration)

    return [
        Error(
            f"New migration {name} for {app} has not been added to migrations list",
            hint="Read the instructions in docs/import-export-logic-updates.rst",
            id='trrf.E002',
        ) for (app, name) in new_migrations
    ]

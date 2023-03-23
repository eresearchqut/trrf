# Generated by Django 3.2.18 on 2023-03-22 10:20
from django.db import migrations
from django.db.models.functions import Lower

from registry.groups import GROUPS as RDRF_GROUPS


def _report_groups(apps):
    Group = apps.get_model('auth', 'Group')
    return Group.objects.annotate(name_lower=Lower('name'))\
                        .filter(name_lower__in=[RDRF_GROUPS.WORKING_GROUP_STAFF,
                                                RDRF_GROUPS.WORKING_GROUP_CURATOR,
                                                RDRF_GROUPS.CLINICAL])


def _can_run_report_permission(apps):
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    content_type = ContentType.objects.filter(app_label='report', model='reportdesign').first()

    if content_type:
        return Permission.objects.filter(codename='can_run_reports',
                                         content_type=content_type).first()


def grant_report_permission_to_groups(apps, schema_editor):
    run_report_perm = _can_run_report_permission(apps)

    if run_report_perm:
        for group in _report_groups(apps):
            group.permissions.add(run_report_perm)


def revoke_report_permission(apps, schema_editor):
    can_run_report = _can_run_report_permission(apps)

    for group in _report_groups(apps):
        group.permissions.remove(can_run_report)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('report', '0003_reportdesign_cde_include_form_timestamp'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reportdesign',
            options={'ordering': ['registry', 'title'], 'permissions': (('can_run_reports', 'Can run reports'),)},
        ),
        migrations.RunPython(grant_report_permission_to_groups, revoke_report_permission),
    ]

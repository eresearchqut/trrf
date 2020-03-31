from django.db import migrations
from django.db.models import Q
from registry.groups import GROUPS as RDRF_GROUPS


def unset_staff_status(apps, schema_editor):
    CustomUser = apps.get_model("groups", "CustomUser")
    base_qs = CustomUser.objects.exclude(is_superuser=True)
    target_groups_filter = (
        Q(groups__name__icontains=RDRF_GROUPS.PARENT) |
        Q(groups__name__icontains=RDRF_GROUPS.CARRIER) |
        Q(groups__name__icontains=RDRF_GROUPS.PATIENT) |
        Q(groups__name__icontains=RDRF_GROUPS.CARER)
    )
    base_qs.filter(target_groups_filter).update(is_staff=False)


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0014_customuser_meta_class_addition'),
    ]

    operations = [
        migrations.RunPython(unset_staff_status, migrations.RunPython.noop)
    ]

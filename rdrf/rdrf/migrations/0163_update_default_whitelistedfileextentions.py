# Generated by Django 3.2.19 on 2023-06-26 10:28
import json

from django.db import migrations

# def _rename_feature(registry, old_feature_name, new_feature_name):
#     if registry.metadata_json:
#         metadata = json.loads(registry.metadata_json)
#         features = metadata.get("features", [])
#         if old_feature_name in features:
#             features.remove(old_feature_name)
#             features.append(new_feature_name)
#             metadata["features"] = features
#             registry.metadata_json = json.dumps(metadata)
#             registry.save()
#
#
def remove_zips(apps, schema_editor):
    WhitelistedFileExtension = apps.get_model('rdrf', 'WhitelistedFileExtension')
    WhitelistedFileExtension.objects.filter(file_extension__in=['.zip', '.gz']).delete()


def rollback_remove_zips(apps, schema_editor):
    WhitelistedFileExtension = apps.get_model('rdrf', 'WhitelistedFileExtension')
    WhitelistedFileExtension.objects.bulk_create([
        WhitelistedFileExtension(file_extension='.zip'),
        WhitelistedFileExtension(file_extension='.gz')])


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0162_rename_email_activation_feature'),
    ]

    operations = [
        migrations.RunPython(remove_zips, rollback_remove_zips)
    ]

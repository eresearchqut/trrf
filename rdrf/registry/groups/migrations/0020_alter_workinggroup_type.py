# Generated by Django 3.2.18 on 2023-05-19 07:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0019_add_working_group_types_and_rules'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workinggroup',
            name='type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='working_groups', to='groups.workinggrouptype'),
        ),
    ]

# Generated by Django 3.2.16 on 2023-01-30 10:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0059_living_status_column_permission'),
        ('rdrf', '0150_decommission_questionnaires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cdefile',
            name='patient',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='patients.patient'),
        ),
    ]
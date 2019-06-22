# Generated by Django 2.1.9 on 2019-06-22 01:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0097_registryform_conditional_rendering_rules'),
        ('patients', '0036_patients_stage'),
    ]

    operations = [
        migrations.AddField(
            model_name='patientstage',
            name='registry',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='rdrf.Registry'),
        ),
    ]

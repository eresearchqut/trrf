# Generated by Django 3.2.18 on 2023-05-17 14:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0060_add_longitudinal_followup_entries'),
    ]

    operations = [
        migrations.CreateModel(
            name='PatientUser',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('patients.patient',),
        ),
    ]

# Generated by Django 2.2.13 on 2020-10-19 17:17

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('patients', '0053_patient_carer_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='registered_clinicians',
            field=models.ManyToManyField(blank=True, related_name='registered_patients', to=settings.AUTH_USER_MODEL),
        ),
    ]

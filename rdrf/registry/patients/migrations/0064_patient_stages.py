# Generated by Django 4.1.13 on 2023-12-20 14:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0063_patientconsent_original_filename'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patientstage',
            name='allowed_next_stages',
            field=models.ManyToManyField(blank=True, related_name='+', to='patients.patientstage'),
        ),
        migrations.AlterField(
            model_name='patientstage',
            name='allowed_prev_stages',
            field=models.ManyToManyField(blank=True, related_name='+', to='patients.patientstage'),
        ),
    ]

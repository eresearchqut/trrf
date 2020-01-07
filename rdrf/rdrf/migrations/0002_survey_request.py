# -*- coding: utf-8 -*-

from django.db import migrations, models

import rdrf.helpers.utils


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('rdrf', '0001_squashed_0118_clinical_data_created_updated_ts'),
        ('patients', '0001_squashed_0051_update_countries_list')
    ]

    operations = [
        migrations.CreateModel(
            name='SurveyRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('patient_token', models.CharField(default=rdrf.helpers.utils.generate_token, max_length=80, unique=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('user', models.CharField(max_length=80)),
                ('state', models.CharField(choices=[('created', 'Created'), ('requested', 'Requested'), ('received', 'Received'), ('error', 'Error')], default='created', max_length=20)),
                ('response', models.TextField(blank=True, null=True)),
                ('patient', models.ForeignKey(on_delete=models.deletion.CASCADE, to='patients.Patient')),
                ('registry', models.ForeignKey(on_delete=models.deletion.CASCADE, to='rdrf.Registry')),
                ('survey_name', models.CharField(max_length=80)),
                ('error_detail', models.TextField(blank=True, null=True)),
                ('communication_type', models.CharField(choices=[('qrcode', 'QRCode'), ('email', 'Email')], default='qrcode', max_length=10)),
            ],
        ),
    ]

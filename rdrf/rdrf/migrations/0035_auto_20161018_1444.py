# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-10-18 14:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0034_filestorage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailnotification',
            name='description',
            field=models.CharField(
                choices=[
                    ('account-locked',
                     'Account Locked'),
                    ('other-clinician',
                     'Other Clinician'),
                    ('new-patient',
                     'New Patient Registered')],
                max_length=100),
        ),
    ]
